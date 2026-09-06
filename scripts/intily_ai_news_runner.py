"""Production entrypoint for Intily with current editorial and source policy."""

import importlib
import json
import os

from intily_scoring_policy import THRESHOLD, calculate


def apply_policy(publisher):
    score_seen = set()
    score_buckets = {
        '0–39': 0, '40–49': 0, '50–59': 0, '60–69': 0,
        '70–79': 0, '80–84': 0, '85–89': 0, '90–100': 0,
    }

    def score(x):
        value, parts = calculate(
            x, publisher.ai_relevant, publisher.HIGH_IMPACT_TERMS,
            publisher.APPLICATION_TERMS, publisher.PRACTICAL_IMPLEMENTATION_TERMS,
            publisher.RISK_AND_PROBLEM_TERMS, publisher.EXCLUSIVITY_TERMS,
            publisher.QUALITY_TRUSTED, publisher.TRUSTED, publisher.LOW_SIGNAL_TERMS,
        )
        x['_score_components'] = parts
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
        return value

    publisher.score = score
    publisher.IMPORTANCE_THRESHOLD = THRESHOLD

    extra_feeds = [
        ('RUSSIA', 'CNews', 'https://www.cnews.ru/inc/rss/news.xml'),
        ('RUSSIA', 'TechCult', 'https://techcult.ru/feed'),
        ('WORLD', 'Euronews', 'https://www.euronews.com/rss?format=mrss&level=theme&name=next'),
    ]
    existing = {row[1] for row in publisher.DIRECT_RSS_FEEDS}
    publisher.DIRECT_RSS_FEEDS = list(publisher.DIRECT_RSS_FEEDS) + [row for row in extra_feeds if row[1] not in existing]
    publisher.QUALITY_TRUSTED = set(publisher.QUALITY_TRUSTED) | {'cnews', 'cnews.ru', 'techcult'}
    publisher.TRUSTED = set(publisher.TRUSTED) | {'cnews', 'cnews.ru', 'techcult', 'euronews'}

    original_collect = publisher.collect

    def collect_with_telemetry(telemetry=None):
        score_seen.clear()
        for key in score_buckets: score_buckets[key] = 0
        result = original_collect(telemetry)
        if telemetry is not None: telemetry['score_buckets'] = dict(score_buckets)
        print('SCORE_BUCKETS', json.dumps(score_buckets, ensure_ascii=False, separators=(',', ':')))
        return result

    publisher.collect = collect_with_telemetry
    publisher.RUSSIA_WEIGHT_BONUS_MIN = 0.0
    publisher.RUSSIA_WEIGHT_BONUS_MAX = 0.0
    publisher.RUSSIA_TARGET_SHARE = -1.0

    def publication_region_boost(state, region):
        history = state.get('publication_regions', [])[-publisher.REGION_HISTORY_SIZE:]
        if not history: return 0.0
        ru_share = history.count('RUSSIA') / len(history)
        tolerance, target = 0.08, 0.60
        if region == 'RUSSIA' and ru_share < target - tolerance: return 50.0
        if region == 'WORLD' and ru_share < target - tolerance: return -12.0
        if region == 'WORLD' and ru_share > target + tolerance: return 20.0
        if region == 'RUSSIA' and ru_share > target + tolerance: return -50.0
        return 0.0

    publisher.publication_region_boost = publication_region_boost


def apply_image_delivery(publisher):
    """Add main-article photo delivery while preserving text-only fallback."""
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

    original_telegram = publisher.telegram
    original_edit = publisher.edit

    def edit_with_context(item, state):
        publisher._current_publication_url = item.get('link', '')
        return original_edit(item, state)

    publisher.edit = edit_with_context

    def telegram_with_image(text):
        token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
        chat_id = os.environ.get('TELEGRAM_CHAT_ID', '@intily')
        article_url = getattr(publisher, '_current_publication_url', '')
        if not token or not article_url:
            telemetry = {
                'status': 'fallback_text', 'attempts': 1, 'method': None, 'url': None,
                'source_url': article_url or None, 'width': None, 'height': None,
                'error': 'missing_token_or_article_url'
            }
            register(telemetry)
            print('IMAGE_FALLBACK_TEXT', telemetry['error'])
            return original_telegram(text)
        telemetry = publish_with_optional_image(text, article_url, token, chat_id, original_telegram)
        register(telemetry)
        publisher._last_image_telemetry = telemetry
        return None

    publisher.telegram = telegram_with_image


if __name__ == '__main__':
    publisher = importlib.import_module('intily_ai_news')
    apply_policy(publisher)
    apply_image_delivery(publisher)
    publisher.main()
