"""Production scoring runtime guard and transparent score diagnostics.

The legacy runner still contains a historical pre-AI +10 audience placeholder.
The guard enforces the canonical stage contract and adds a compact, explicit
score breakdown to every published post. The breakdown is intentionally added
before the image delivery layer so the photo-caption safety policy can decide
whether the complete post fits Telegram's caption limit; editorial text is never
truncated to make room for diagnostics.
"""

import functools
import html


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
    if penalty:
        lines.append(f'Шум/низкий сигнал: −{penalty:.1f}')
    else:
        lines.append('Шум/низкий сигнал: 0.0')

    if audience_score is not None:
        lines.append(f'Аудитория: {float(audience_score):.0f}/10 → +{audience_bonus:.1f}')
    else:
        lines.append('Аудитория: ещё не оценена')
    return '\n'.join(lines)


def _attach_score_footer(item, post):
    """Append diagnostics without ever truncating the editorial post."""
    footer = _score_footer(item)
    candidate = str(post or '').rstrip() + '\n' + footer
    # Telegram text messages are limited to 4096 characters. Photo captions are
    # stricter at 1024; image runtime will deliberately fall back to full text
    # if the complete caption is too long. Never slice the candidate here.
    if len(candidate) > 4096:
        raise RuntimeError('SCORE_DIAGNOSTICS_TEXT_LIMIT')
    return candidate


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

    # The runner's editorial wrapper has already performed AI audience scoring.
    # Add the transparent breakdown immediately before main() starts publication,
    # so both photo and text delivery receive exactly the same complete content.
    original_edit = publisher.edit

    @functools.wraps(original_edit)
    def edit_with_score_footer(item, state):
        post = original_edit(item, state)
        item['_score_components'] = dict(item.get('_score_components') or {})
        post = _attach_score_footer(item, post)
        item['post'] = post
        return post

    publisher.edit = edit_with_score_footer
    publisher.main()


if __name__ == '__main__':
    run_production()
