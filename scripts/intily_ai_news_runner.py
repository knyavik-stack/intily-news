"""Production entrypoint for Intily: editorial, CMO audience, geography and media policy."""

import importlib
import json
import os
import re

from intily_scoring_policy import THRESHOLD, calculate
from intily_audience_policy import (
    PRE_AI_THRESHOLD,
    FINAL_THRESHOLD,
    bonus_from_score,
    build_evaluation_instruction,
    clamp_score,
)


def apply_policy(publisher):
    score_seen = set()
    score_buckets = {
        '0–39': 0, '40–49': 0, '50–59': 0, '60–69': 0,
        '70–79': 0, '80–84': 0, '85–89': 0, '90–100': 0,
    }
    audience_buckets = {str(i): 0 for i in range(1, 11)}
    publisher._cycle_audience = {
        'evaluated': 0, 'scores': [], 'bonus_total': 0.0,
        'final_buckets': {k: 0 for k in score_buckets},
        'last': None,
    }

    def score(x):
        base_value, parts = calculate(
            x, publisher.ai_relevant, publisher.HIGH_IMPACT_TERMS,
            publisher.APPLICATION_TERMS, publisher.PRACTICAL_IMPLEMENTATION_TERMS,
            publisher.RISK_AND_PROBLEM_TERMS, publisher.EXCLUSIVITY_TERMS,
            publisher.QUALITY_TRUSTED, publisher.TRUSTED, publisher.LOW_SIGNAL_TERMS,
        )
        audience_score = x.get('audience_score')
        audience_bonus = 0.0
        if audience_score is not None:
            try:
                audience_score = clamp_score(audience_score)
                audience_bonus = bonus_from_score(audience_score)
            except Exception:
                audience_score = None
        value = round(min(100.0, base_value + audience_bonus), 1)
        parts['base_score'] = round(base_value, 1)
        parts['audience_score'] = audience_score
        parts['audience_bonus'] = audience_bonus
        parts['final_score'] = value
        x['_score_components'] = parts
        x['base_score'] = round(base_value, 1)
        x['audience_bonus'] = audience_bonus
        x['score_stage'] = 'final' if audience_score is not None else 'pre_ai'
        identity = id(x)
        if identity not in score_seen:
            score_seen.add(identity)
            if value < 40: bucket = '0–39'
            elif value < 50: bucket = '40–49'
            elif value < 60: bucket = '50–59'
            elif value < 70: bucket = '60–69'
            elif value < 80: bucket = '70–79'
            elif value < 85: bucket = '80–84'
            elif value < 90: bucket = '85–89'
            else: bucket = '90–100'
            score_buckets[bucket] += 1
            if audience_score is not None:
                audience_buckets[str(int(audience_score))] += 1
        return value

    publisher.score = score
    # Stage 1 is intentionally wider: only material stories reach the AI editor.
    publisher.IMPORTANCE_THRESHOLD = PRE_AI_THRESHOLD
    publisher.FINAL_IMPORTANCE_THRESHOLD = FINAL_THRESHOLD

    # Russian discovery is expanded by job-to-be-done, not only by AI-company names.
    extra_feeds = [
        ('RUSSIA', 'CNews', 'https://www.cnews.ru/inc/rss/news.xml'),
        ('WORLD', 'Euronews', 'https://www.euronews.com/rss'),
    ]
    existing = {row[1] for row in publisher.DIRECT_RSS_FEEDS}
    publisher.DIRECT_RSS_FEEDS = list(publisher.DIRECT_RSS_FEEDS) + [
        row for row in extra_feeds if row[1] not in existing
    ]

    extra_queries = [
        ('RUSSIA', 'site:techcult.ru ИИ искусственный интеллект'),
        ('RUSSIA', 'site:techcult.ru искусственный интеллект модели роботы'),
        ('RUSSIA', 'ИИ российский бизнес автоматизация продажи маркетинг сервис'),
        ('RUSSIA', 'ИИ малый средний бизнес Россия внедрение продуктивность'),
        ('RUSSIA', 'российские нейросети AI агенты продукты сервисы компании'),
        ('RUSSIA', 'Яндекс Сбер GigaChat Alice AI новые модели продукты'),
        ('RUSSIA', 'VK МТС Мегафон Ozon Avito AI искусственный интеллект'),
        ('RUSSIA', 'ИИ финансы банки страхование Россия автоматизация'),
        ('RUSSIA', 'ИИ промышленность производство логистика ритейл Россия'),
        ('RUSSIA', 'ИИ медицина образование HR юристы Россия применение'),
        ('RUSSIA', 'ИИ кибербезопасность утечка мошенничество Россия'),
        ('RUSSIA', 'ИИ регулирование закон персональные данные Россия'),
        ('RUSSIA', 'ИИ инвестиции стартапы венчур Россия'),
        ('RUSSIA', 'роботы агенты компьютерное зрение Россия технологии'),
        ('RUSSIA', 'импортозамещение ИИ инфраструктура GPU датацентры Россия'),
        ('RUSSIA', 'site:rbc.ru ИИ бизнес технологии Россия'),
        ('RUSSIA', 'site:kommersant.ru ИИ бизнес технологии Россия'),
        ('RUSSIA', 'site:vc.ru ИИ бизнес автоматизация Россия'),
        ('RUSSIA', 'site:tass.ru ИИ искусственный интеллект технологии'),
    ]
    existing_queries = set(publisher.QUERIES)
    publisher.QUERIES = list(publisher.QUERIES) + [
        row for row in extra_queries if row not in existing_queries
    ]

    publisher.QUALITY_TRUSTED = set(publisher.QUALITY_TRUSTED) | {
        'cnews', 'cnews.ru', 'cnbc', 'bbc', 'the wall street journal', 'wsj',
        'axios', 'the register', 'the information', 'рбк', 'rbc.ru',
    }
    publisher.TRUSTED = set(publisher.TRUSTED) | {
        'cnews', 'cnews.ru', 'euronews', 'cnbc', 'bbc', 'wsj', 'axios',
        'the register', 'рбк', 'rbc.ru',
    }

    original_build_prompt = publisher.build_edit_prompt
    def build_prompt_with_audience(x, retry=False, previous_error=''):
        return original_build_prompt(x, retry=retry, previous_error=previous_error) + build_evaluation_instruction()
    publisher.build_edit_prompt = build_prompt_with_audience

    original_parse_json = publisher.parse_editor_json
    def parse_editor_json_with_audience(raw):
        parsed = original_parse_json(raw)
        value = parsed.get('audience_score')
        if value is None:
            raise RuntimeError('AUDIENCE_SCORE_MISSING')
        audience_score = clamp_score(value)
        publisher._last_ai_audience = {
            'score': audience_score,
            'reason': str(parsed.get('audience_reason', '') or '').strip()[:240],
        }
        return parsed
    publisher.parse_editor_json = parse_editor_json_with_audience

    original_edit = publisher.edit
    def edit_with_audience(x, state):
        publisher._last_ai_audience = None
        post = original_edit(x, state)
        audience = publisher._last_ai_audience
        if not audience:
            raise RuntimeError('AUDIENCE_SCORE_UNAVAILABLE')
        audience_score = clamp_score(audience['score'])
        audience_bonus = bonus_from_score(audience_score)
        x['audience_score'] = audience_score
        x['audience_bonus'] = audience_bonus
        final_score = publisher.score(x)
        x['importance'] = final_score
        x['score'] = final_score
        x['tier'] = publisher.tier(x)
        x['score_stage'] = 'final'
        stats = publisher._cycle_audience
        stats['evaluated'] += 1
        stats['scores'].append(audience_score)
        stats['bonus_total'] += audience_bonus
        stats['last'] = {
            'score': audience_score,
            'bonus': audience_bonus,
            'reason': audience.get('reason', ''),
            'title': x.get('title', ''),
            'final_score': final_score,
        }
        print('AUDIENCE_SCORE', json.dumps(stats['last'], ensure_ascii=False, separators=(',', ':')))
        if final_score < FINAL_THRESHOLD:
            raise RuntimeError(f'FINAL_SCORE_BELOW_THRESHOLD:{final_score}')
        return post
    publisher.edit = edit_with_audience

    original_collect = publisher.collect
    def collect_with_telemetry(telemetry=None):
        score_seen.clear()
        for key in score_buckets:
            score_buckets[key] = 0
        result = original_collect(telemetry)
        if telemetry is not None:
            telemetry['score_buckets'] = dict(score_buckets)
            telemetry['audience_buckets'] = dict(audience_buckets)
            telemetry['audience_stage'] = 'post_editorial'
        print('SCORE_BUCKETS', json.dumps(score_buckets, ensure_ascii=False, separators=(',', ':')))
        print('AUDIENCE_BUCKETS', json.dumps(audience_buckets, ensure_ascii=False, separators=(',', ':')))
        return result
    publisher.collect = collect_with_telemetry

    original_record_kpi = publisher.record_kpi
    def record_kpi_with_audience(s, now, searched, candidates, queue_before, queue_after,
                                 published, publish_attempts, item_failures, business_result,
                                 business_reason, admission=None, rss_telemetry=None,
                                 provider_telemetry=None, duration_sec=0.0):
        admission_copy = dict(admission or {})
        stats = publisher._cycle_audience
        scores = list(stats.get('scores', []))
        queue_items = list(s.get('queue', []) or [])
        pre_ai_below_final = sum(
            1 for item in queue_items
            if item.get('score_stage', 'pre_ai') != 'final'
            and float(item.get('importance', item.get('score', 0)) or 0) < FINAL_THRESHOLD
        )
        final_below_threshold = sum(
            1 for item in queue_items
            if item.get('score_stage') == 'final'
            and float(item.get('importance', item.get('score', 0)) or 0) < FINAL_THRESHOLD
        )
        admission_copy['audience'] = {
            'evaluated': int(stats.get('evaluated', 0)),
            'average_score': round(sum(scores) / len(scores), 2) if scores else None,
            'bonus_total': round(float(stats.get('bonus_total', 0.0)), 1),
            'max_score': max(scores) if scores else None,
            'high_fit_8_10': sum(1 for value in scores if value >= 8),
            'last': stats.get('last'),
        }
        admission_copy['queue_score_audit'] = {
            'pre_ai_below_final_threshold': pre_ai_below_final,
            'final_below_threshold': final_below_threshold,
            'invariant_ok': final_below_threshold == 0,
        }
        print('AUDIENCE_KPI', json.dumps(admission_copy['audience'], ensure_ascii=False, separators=(',', ':')))
        print('QUEUE_SCORE_AUDIT', json.dumps(admission_copy['queue_score_audit'], ensure_ascii=False, separators=(',', ':')))
        return original_record_kpi(
            s, now, searched, candidates, queue_before, queue_after,
            published, publish_attempts, item_failures, business_result, business_reason,
            admission=admission_copy, rss_telemetry=rss_telemetry,
            provider_telemetry=provider_telemetry, duration_sec=duration_sec
        )
    publisher.record_kpi = record_kpi_with_audience

    # Geographic mix is a portfolio objective, not a relevance bonus.
    publisher.RUSSIA_WEIGHT_BONUS_MIN = 5.0
    publisher.RUSSIA_WEIGHT_BONUS_MAX = 10.0
    publisher.RUSSIA_TARGET_SHARE = -1.0  # do not hard-filter WORLD while RU is scarce

    def publication_region_boost(state, region):
        history = state.get('publication_regions', [])[-publisher.REGION_HISTORY_SIZE:]
        if not history:
            return 0.0
        ru_share = history.count('RUSSIA') / len(history)
        tolerance, target = 0.05, 0.40
        if region == 'RUSSIA' and ru_share < target - tolerance:
            return 35.0
        if region == 'WORLD' and ru_share < target - tolerance:
            return -8.0
        if region == 'WORLD' and ru_share > target + tolerance:
            return 10.0
        if region == 'RUSSIA' and ru_share > target + tolerance:
            return -25.0
        return 0.0
    publisher.publication_region_boost = publication_region_boost


def apply_image_delivery(publisher):
    """Publisher-first image delivery with hard validation and Google-host ban."""
    from intily_google_news import resolve as resolve_google_news
    from intily_image_pipeline import publish_with_optional_image

    publisher._cycle_image_telemetry = {
        'attempts': 0, 'found': 0, 'validated': 0, 'photo_sent': 0,
        'text_fallback': 0, 'fallback_reasons': {}, 'sources': {}, 'last': None,
    }

    def register(telemetry):
        if not telemetry:
            return
        stats = publisher._cycle_image_telemetry
        stats['attempts'] += int(telemetry.get('attempts', 0) or 0)
        status = telemetry.get('status')
        if status == 'sent':
            stats['found'] += 1
            stats['validated'] += 1
            stats['photo_sent'] += 1
            method = telemetry.get('method') or 'unknown'
            stats['sources'][method] = stats['sources'].get(method, 0) + 1
        elif status == 'fallback_text':
            stats['text_fallback'] += 1
            reason = str(telemetry.get('error') or 'unknown')[:160]
            stats['fallback_reasons'][reason] = stats['fallback_reasons'].get(reason, 0) + 1
        stats['last'] = {
            'status': status, 'method': telemetry.get('method'),
            'source_url': telemetry.get('source_url'), 'image_url': telemetry.get('url'),
            'width': telemetry.get('width'), 'height': telemetry.get('height'),
            'error': telemetry.get('error'),
        }

    original_record_kpi = publisher.record_kpi
    def record_kpi_with_image(s, now, searched, candidates, queue_before, queue_after,
                              published, publish_attempts, item_failures, business_result,
                              business_reason, admission=None, rss_telemetry=None,
                              provider_telemetry=None, duration_sec=0.0):
        admission_copy = dict(admission or {})
        image_stats = publisher._cycle_image_telemetry
        admission_copy['image'] = {
            'attempts': int(image_stats.get('attempts', 0)),
            'found': int(image_stats.get('found', 0)),
            'validated': int(image_stats.get('validated', 0)),
            'photo_sent': int(image_stats.get('photo_sent', 0)),
            'text_fallback': int(image_stats.get('text_fallback', 0)),
            'fallback_reasons': dict(image_stats.get('fallback_reasons', {})),
            'sources': dict(image_stats.get('sources', {})),
            'last': image_stats.get('last'),
        }
        print('IMAGE_KPI', json.dumps(admission_copy['image'], ensure_ascii=False, separators=(',', ':')))
        return original_record_kpi(
            s, now, searched, candidates, queue_before, queue_after,
            published, publish_attempts, item_failures, business_result, business_reason,
            admission=admission_copy, rss_telemetry=rss_telemetry,
            provider_telemetry=provider_telemetry, duration_sec=duration_sec
        )
    publisher.record_kpi = record_kpi_with_image

    original_telegram = publisher.telegram
    original_edit_context = publisher.edit
    def edit_with_context(item, state):
        publisher._current_publication_url = item.get('link', '')
        return original_edit_context(item, state)
    publisher.edit = edit_with_context

    def telegram_with_image(text):
        token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
        chat_id = os.environ.get('TELEGRAM_CHAT_ID', '@intily')
        article_url = getattr(publisher, '_current_publication_url', '')
        resolved_url = resolve_google_news(article_url)
        if not token or not resolved_url:
            telemetry = {
                'status': 'fallback_text', 'attempts': 1, 'method': None, 'url': None,
                'source_url': resolved_url or article_url or None, 'width': None, 'height': None,
                'error': 'missing_token_or_article_url'
            }
            register(telemetry)
            print('IMAGE_FALLBACK_TEXT', telemetry['error'])
            return original_telegram(text)
        if resolved_url != article_url:
            print('IMAGE_SOURCE_RESOLVED', resolved_url)
        # The base publisher currently labels this as a "weight" even though it
        # is pre-AI. Make the diagnostic truthful: 58.7 is a pre-AI candidate
        # weight, not a violation of the final 60 publication gate.
        text = re.sub(
            r'Следующая в очереди имеет вес ([0-9]+(?:\.[0-9])?)%\.',
            r'Следующая в очереди: базовый вес \1/100; AI-аудит ещё не проведён.',
            text,
        )
        telemetry = publish_with_optional_image(text, resolved_url, token, chat_id, original_telegram)
        register(telemetry)
        publisher._last_image_telemetry = telemetry
        return None
    publisher.telegram = telegram_with_image


if __name__ == '__main__':
    publisher = importlib.import_module('intily_ai_news')
    apply_policy(publisher)
    apply_image_delivery(publisher)
    publisher.main()
