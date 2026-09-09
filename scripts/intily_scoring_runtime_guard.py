"""Production scoring runtime guard, final-score ordering and score diagnostics.

The legacy runner contains historical scoring behavior that must not leak into
production ordering: a pre-AI +10 placeholder, regional priority and a quota
rebalance that can displace a higher-scoring story. This adapter enforces the
canonical contract: deterministic base -> AI audience -> final score -> queue
ordering/publication, with geography kept outside the mathematical score.
"""

import functools
import re
import time


SCORE_COMPONENT_LABELS = (
    ('relevance', 'AI-релевантность', 12.0),
    ('ai_specificity', 'AI-специфичность', 6.0),
    ('impact', 'Влияние', 16.0),
    ('event_concreteness', 'Конкретность события', 18.0),
    ('practical_value', 'Практическая ценность', 8.0),
    ('novelty', 'Новизна', 0.0),
    ('source_quality', 'Качество источника', 5.0),
    ('evidence', 'Доказательность', 3.0),
    ('freshness', 'Свежесть', 2.0),
)


def _score_footer(item):
    components = item.get('_score_components') or {}
    final_score = float(components.get('final_score', item.get('score', item.get('importance', 0))) or 0)
    base_score = float(components.get('base_score', item.get('base_score', 0)) or 0)
    audience_score = components.get('audience_score', item.get('audience_score'))
    audience_bonus = float(components.get('audience_bonus', item.get('audience_bonus', 0)) or 0)
    penalty = float(components.get('low_signal_penalty', 0) or 0)

    lines = [
        '',
        '📊 <b>Оценка новости</b>',
        f'<b>Итого: {final_score:.1f}/100</b> = база {base_score:.1f}/70 + аудитория {audience_bonus:.1f}/30',
    ]
    for key, label, maximum in SCORE_COMPONENT_LABELS:
        value = float(components.get(key, 0) or 0)
        lines.append(f'{label}: {value:.1f}/{maximum:.0f}')
    lines.append(f'Шум/низкий сигнал: −{penalty:.1f}' if penalty else 'Шум/низкий сигнал: 0.0')
    if audience_score is not None:
        lines.append(f'Аудитория: {float(audience_score):.0f}/10 → +{audience_bonus:.1f}')
    else:
        lines.append('Аудитория: ещё не оценена')
    return '\n'.join(lines)


def _final_score(item):
    components = item.get('_score_components') or {}
    return float(components.get('final_score', item.get('importance', item.get('score', 0.0))) or 0.0)


def _is_final(item):
    return item.get('score_stage') == 'final' and item.get('audience_score') is not None


def _attach_score_footer(item, post):
    """Append diagnostics without ever truncating the editorial post."""
    candidate = str(post or '').rstrip() + '\n' + _score_footer(item)
    if len(candidate) > 4096:
        raise RuntimeError('SCORE_DIAGNOSTICS_TEXT_LIMIT')
    return candidate


def _base_recalculate(publisher, item):
    """Remove legacy RU bonus and make importance equal to deterministic base."""
    item.pop('russia_weight_bonus', None)
    item['audience_score'] = None
    base = float(publisher.score(item))
    item['score'] = round(base, 1)
    item['importance'] = round(base, 1)
    item['base_score'] = round(base, 1)
    item['audience_bonus'] = 0.0
    item['score_stage'] = 'pre_ai'
    return base


def _final_sort_key(item):
    """Final items outrank pending pre-AI items; score is always primary."""
    return (
        1 if _is_final(item) else 0,
        _final_score(item),
        float(item.get('time', 0.0) or 0.0),
    )


def _pure_score_rebalance(publisher, items, now):
    """Keep the best qualifying stories; never let geography displace score."""
    fresh = []
    for item in items or []:
        try:
            publisher.normalize_item_text(item)
        except Exception:
            pass
        if float(item.get('time', 0) or 0) < now - publisher.LOOKBACK.total_seconds():
            continue
        if not publisher.candidate_quality(item):
            continue
        fresh.append(item)

    fresh.sort(key=_final_sort_key, reverse=True)
    unique = []
    for item in fresh:
        if any(publisher.same_story(item, other) for other in unique):
            continue
        unique.append(item)
    return unique[:publisher.MAX_QUEUE]


class PublisherScoreProxy:
    """Proxy that guards the score function installed by the legacy runner."""

    def __init__(self, module):
        object.__setattr__(self, '_module', module)

    def __getattr__(self, name):
        return getattr(self._module, name)

    def __setattr__(self, name, value):
        if name == 'score' and callable(value):
            @functools.wraps(value)
            def guarded_score(item):
                result = value(item)
                if item.get('audience_score') is None:
                    components = item.get('_score_components') or {}
                    base_score = round(float(components.get('base_score', result)), 1)
                    components['audience_bonus'] = 0.0
                    components['final_score'] = base_score
                    item['_score_components'] = components
                    item['audience_bonus'] = 0.0
                    item['score_stage'] = 'pre_ai'
                    return base_score
                return result

            setattr(self._module, name, guarded_score)
            return
        setattr(self._module, name, value)


def run_production():
    import importlib

    runner = importlib.import_module('intily_ai_news_runner')
    publisher_module = importlib.import_module('intily_ai_news')
    publisher = PublisherScoreProxy(publisher_module)

    runner.apply_policy(publisher)
    runner.apply_image_delivery(publisher)

    # Final score is the sole publication priority. Pre-AI items are pending and
    # must never outrank an already-finalized item.
    publisher.publication_priority = lambda state, item: (
        _final_score(item) if _is_final(item) else -1.0
    )

    # The legacy rebalance enforces a regional quota and can therefore discard a
    # higher-scoring story. Replace it with a pure score-capacity rebalance.
    publisher.rebalance_queue = lambda items, now: _pure_score_rebalance(publisher, items, now)

    original_edit = publisher.edit
    post_cache = {}

    @functools.wraps(original_edit)
    def edit_with_score_footer(item, state):
        key = item.get('key') or item.get('link') or item.get('title')
        cached = post_cache.get(key)
        if cached is not None:
            return cached
        post = original_edit(item, state)
        # Remove legacy pre-AI queue wording. The main publisher appends the
        # authoritative queue diagnostic after its own final-score rebalance.
        post = re.sub(
            r'Следующая в очереди: базовый вес [0-9]+(?:\.[0-9])?/100; AI-аудит ещё не проведён\.',
            '',
            post,
        )
        post = re.sub(
            r'Следующая в очереди имеет вес [0-9]+(?:\.[0-9])?%\.',
            '',
            post,
        )
        post = _attach_score_footer(item, post)
        post_cache[key] = post
        return post

    publisher.edit = edit_with_score_footer

    def evaluate_item(item, state):
        """Run the real AI editorial layer once and cache its complete post."""
        if _is_final(item):
            return True
        try:
            _base_recalculate(publisher, item)
            edit_with_score_footer(item, state)
            return _is_final(item)
        except Exception as exc:
            print('FINAL_SCORE_PRECHECK_FAILED', str(item.get('title', ''))[:160], str(exc)[:240])
            try:
                _base_recalculate(publisher, item)
            except Exception:
                pass
            return False

    original_load_state = publisher.load_state

    def load_state_with_final_score_precheck(*args, **kwargs):
        state = original_load_state(*args, **kwargs)
        now = time.time()
        published = state.get('published', {})
        for item in list(state.get('queue', []) or []):
            if item.get('key') in published or item.get('legacy_key') in published:
                continue
            if float(item.get('time', 0) or 0) < now - publisher.LOOKBACK.total_seconds():
                continue
            if not _is_final(item):
                evaluate_item(item, state)
        state['queue'] = _pure_score_rebalance(publisher, state.get('queue', []), now)
        print('FINAL_SCORE_QUEUE_PRECHECK', len(state.get('queue', []) or []))
        return state

    publisher.load_state = load_state_with_final_score_precheck

    original_collect = publisher.collect

    def collect_with_final_score_precheck(telemetry=None):
        candidates = original_collect(telemetry)
        state = None
        for item in candidates:
            _base_recalculate(publisher, item)
            # Candidates are evaluated before main() admits them to durable queue.
            # This is the critical new-search -> final-score -> queue contract.
            evaluate_item(item, state)
        candidates.sort(key=_final_sort_key, reverse=True)
        print('FINAL_SCORE_CANDIDATES_SORTED', len(candidates))
        return candidates

    publisher.collect = collect_with_final_score_precheck

    publisher.main()


if __name__ == '__main__':
    run_production()
