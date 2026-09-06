#!/usr/bin/env python3
"""Русская панель производственного мониторинга Intily.

Читает только data/intily-ai-news-state.json. Не обращается к Telegram, RSS или
AI-провайдерам. GitHub Actions Summary является интерфейсом оператора.
"""
import argparse
import json
import time
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parents[1] / 'data' / 'intily-ai-news-state.json'

# Жёсткие пороги аварийного состояния. Это технические пороги, а не редакционные цели.
ALERT_NO_PUBLISH_RUNS = 10
ALERT_PUBLISH_FAILURES_24H = 5
ALERT_PUBLISH_FAILURE_RATE = 20.0
ALERT_RSS_ERROR_RATE = 25.0

# Диагностические пороги показываются как предупреждения и не ломают workflow.
WARN_PUBLISH_FAILURES_24H = 3
WARN_PUBLISH_FAILURE_RATE = 10.0
WARN_ADMISSION_RATE = 10.0
MIN_RATE_SAMPLE_ATTEMPTS = 10
MIN_ADMISSION_SAMPLE = 50

RESULT_LABELS = {
    'PUBLISHED': 'ОПУБЛИКОВАНО',
    'NO_PUBLISH': 'НЕ ОПУБЛИКОВАНО',
    'PUBLISH_FAILED': 'ОШИБКА ПУБЛИКАЦИИ',
}

REASON_LABELS = {
    'telegram_delivery_ok': 'публикация в Telegram выполнена',
    'empty_queue_after_filters': 'после отбора очередь пуста',
    'publish_interval_not_reached': 'интервал между публикациями ещё не истёк',
    'admission_blocked_published_key': 'кандидаты уже были опубликованы ранее',
    'admission_blocked_candidate_count': 'новых кандидатов недостаточно для добавления',
    'no_candidates_and_empty_queue': 'нет новых кандидатов и очередь пуста',
}

BLOCK_LABELS = {
    'published_key': 'уже опубликовано ранее',
    'known_recent': 'недавно уже обрабатывалось',
    'already_queued': 'уже находится в очереди',
    'story_queue': 'та же история уже находится в очереди',
    'story_history': 'та же история уже была опубликована недавно',
    'candidate_count': 'недостаточно новых кандидатов',
    'none': 'нет блокировки',
}

PROVIDER_LABELS = {
    'GEMINI': 'Gemini',
    'GROQ': 'Groq',
    'OPENAI': 'OpenAI',
}


def load(path=STATE_PATH):
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def rows(state):
    return state.get('run_history', []) if state.get('kpi_monitoring_enabled', True) else []


def window(data, seconds, now):
    return [r for r in data if now - float(r.get('ts', 0) or 0) <= seconds]


def sums(data):
    pubs = sum(int(r.get('published', 0) or 0) for r in data)
    attempts = sum(int(r.get('publish_attempts', 0) or 0) for r in data)
    failures = sum(int(r.get('item_failures', 0) or 0) for r in data)
    candidates = sum(int(r.get('candidates', 0) or 0) for r in data)
    rss_candidates = sum(int(r.get('rss', {}).get('candidates', 0) or 0) for r in data if r.get('rss'))
    admission_rows = [r for r in data if r.get('admission') and 'candidate_count' in r.get('admission', {})]
    observed_candidates = sum(int(r.get('admission', {}).get('candidate_count', 0) or 0) for r in admission_rows)
    added = sum(int(r.get('admission', {}).get('added', 0) or 0) for r in admission_rows)
    no_publish = sum(1 for r in data if r.get('business_result') == 'NO_PUBLISH')
    no_publish_reasons = {}
    admission_blocks = {}
    provider_used = {}
    failovers = 0
    rss_raw = rss_errors = rss_attempts = direct_raw = direct_errors = 0
    source_counts = {}
    q_values = [float(r.get('queue_after', 0) or 0) for r in data]
    q_deltas = [float(r.get('queue_after', 0) or 0) - float(r.get('queue_before', 0) or 0) for r in data]
    pub_ts = [float(r.get('ts', 0) or 0) for r in data if r.get('published')]

    for r in data:
        if r.get('business_result') == 'NO_PUBLISH':
            reason = r.get('business_reason', 'unknown')
            no_publish_reasons[reason] = no_publish_reasons.get(reason, 0) + 1
        a = r.get('admission', {})
        block = a.get('dominant_block')
        if block and block != 'none':
            admission_blocks[block] = admission_blocks.get(block, 0) + 1
        p = r.get('provider', {})
        used = p.get('used')
        if used:
            provider_used[used] = provider_used.get(used, 0) + 1
        failovers += int(p.get('failovers', 0) or 0)
        rss = r.get('rss', {})
        rss_raw += int(rss.get('raw_items', 0) or 0)
        rss_errors += int(rss.get('query_errors', 0) or 0)
        rss_attempts += int(rss.get('queries_attempted', 0) or 0)
        direct_raw += int(rss.get('direct_raw_items', 0) or 0)
        direct_errors += int(rss.get('direct_feed_errors', 0) or 0)
        for source, count in rss.get('source_counts', {}).items():
            # -1 означает ошибку ленты; ошибка уже учитывается отдельно.
            source_counts[source] = source_counts.get(source, 0) + max(0, int(count or 0))

    intervals = [(b - a) / 60 for a, b in zip(pub_ts, pub_ts[1:]) if b > a]
    span_hours = (data[-1]['ts'] - data[0]['ts']) / 3600 if len(data) > 1 else 0
    return {
        'cycles': len(data),
        'searches': sum(1 for r in data if r.get('searched')),
        'candidates': candidates,
        'rss_candidates': rss_candidates,
        'avg_candidates': candidates / max(1, len(data)),
        'published': pubs,
        'publication_rate': pubs / max(1, len(data)) * 100,
        'publish_frequency': pubs / max(1, span_hours) if span_hours else 0,
        'avg_publish_interval': sum(intervals) / len(intervals) if intervals else None,
        'attempts': attempts,
        'failures': failures,
        'failure_rate': failures / max(1, attempts) * 100,
        'no_publish': no_publish,
        'no_publish_rate': no_publish / max(1, len(data)) * 100,
        'no_publish_reasons': no_publish_reasons,
        'admission_candidates': observed_candidates,
        'admission_added': added,
        'admission_rate': added / max(1, observed_candidates) * 100,
        'admission_blocks': admission_blocks,
        'rss_raw': rss_raw,
        'rss_errors': rss_errors,
        'rss_attempts': rss_attempts,
        'direct_raw': direct_raw,
        'direct_errors': direct_errors,
        'source_counts': source_counts,
        'rss_error_rate': rss_errors / max(1, rss_attempts) * 100,
        'provider_used': provider_used,
        'failovers': failovers,
        'queue_avg': sum(q_values) / len(q_values) if q_values else 0,
        'queue_max': max(q_values) if q_values else 0,
        'queue_velocity': sum(q_deltas) / len(q_deltas) if q_deltas else 0,
    }


def pct(value):
    return f'{value:.1f}%'


def top_items(mapping, limit=6):
    return sorted(mapping.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]


def reason_label(value):
    return REASON_LABELS.get(value, value or 'не указана')


def block_label(value):
    return BLOCK_LABELS.get(value, value or 'не определена')


def print_dashboard(state):
    data = rows(state)
    now = time.time()
    d24 = sums(window(data, 86400, now))
    d7 = sums(window(data, 7 * 86400, now))
    stored = sums(data)
    health = state.get('health', {})
    last = data[-1] if data else {}
    consecutive_no_publish = 0
    for r in reversed(data):
        if r.get('business_result') == 'NO_PUBLISH':
            consecutive_no_publish += 1
        else:
            break

    hard, warnings = evaluate(data, d24)
    status = '🔴 КРИТИЧЕСКОЕ СОСТОЯНИЕ' if hard else ('🟡 ТРЕБУЕТ ВНИМАНИЯ' if warnings else '🟢 НОРМА')
    last_result = RESULT_LABELS.get(last.get('business_result'), last.get('business_result', 'НЕИЗВЕСТНО'))
    last_reason = reason_label(last.get('business_reason', ''))

    print(f'# Intily Production Monitor — {status}')
    print('')
    print(f'> **Последний запуск:** **{last_result}** — {last_reason}.')
    print(f'> **Техническое состояние:** **{health.get("last_status", "НЕИЗВЕСТНО")}** · **Очередь:** {len(state.get("queue", []))} · **Запусков без публикации подряд:** {consecutive_no_publish}')
    print('')

    print('## Основные показатели')
    print('')
    print('| Показатель | 24 часа | 7 дней | Сохранённая история |')
    print('|---|---:|---:|---:|')
    print(f"| Запуски | {d24['cycles']} | {d7['cycles']} | {stored['cycles']} |")
    print(f"| Публикации | {d24['published']} | {d7['published']} | {stored['published']} |")
    print(f"| Доля запусков с публикацией | {pct(d24['publication_rate'])} | {pct(d7['publication_rate'])} | {pct(stored['publication_rate'])} |")
    print(f"| Средняя частота публикаций | {d24['publish_frequency']:.2f}/ч | {d7['publish_frequency']:.2f}/ч | — |")
    print(f"| Кандидаты | {d24['candidates']} | {d7['candidates']} | {stored['candidates']} |")
    print(f"| Без публикации | {d24['no_publish']} ({pct(d24['no_publish_rate'])}) | {d7['no_publish']} ({pct(d7['no_publish_rate'])}) | {stored['no_publish']} |")
    print(f"| Ошибки публикации | {d24['failures']} ({pct(d24['failure_rate'])}) | {d7['failures']} ({pct(d7['failure_rate'])}) | {stored['failures']} |")
    print('')

    print('## Поток новостей: поиск → отбор → очередь → публикация')
    print('')
    print('| Этап | 24 часа | Что означает |')
    print('|---|---:|---|')
    print(f"| Получено из RSS | {d24['rss_raw']} | все полученные материалы |")
    print(f"| Кандидаты RSS | {d24['rss_candidates']} | {pct(d24['rss_candidates'] / max(1, d24['rss_raw']) * 100)} от материалов RSS |")
    print(f"| Кандидаты запусков | {d24['candidates']} | прошли редакционный отбор |")
    print(f"| Добавлено в очередь | {d24['admission_added']} | новые истории после защиты от повторов |")
    print(f"| Опубликовано | {d24['published']} | публикации за запуски; часть могла прийти из очереди прошлых запусков |")
    print(f"| Изменение очереди | {d24['queue_velocity']:+.2f}/запуск | среднее изменение размера очереди |")
    print('')

    print('## Здоровье источников и AI')
    print('')
    print('| Показатель | 24 часа |')
    print('|---|---:|')
    print(f"| Поисковые запросы Google News | {d24['rss_attempts']} попыток / {d24['rss_errors']} ошибок |")
    print(f"| Прямые RSS-ленты | {d24['direct_raw']} материалов / {d24['direct_errors']} ошибок |")
    print(f"| Доля ошибок поисковых запросов | {pct(d24['rss_error_rate'])} |")
    providers = ', '.join(f'{PROVIDER_LABELS.get(k, k)}: {v}' for k, v in top_items(d24['provider_used'])) or 'нет данных за период'
    print(f"| Использованные AI-провайдеры | {providers} |")
    print(f"| Переключения на резервного провайдера | {d24['failovers']} |")
    print('')

    if d24['source_counts']:
        print('### Какие прямые источники дают материал')
        print('')
        print('| Источник | Материалов |')
        print('|---|---:|')
        for source, count in top_items(d24['source_counts'], 8):
            print(f'| {source} | {count} |')
        print('')

    print('## Почему иногда ничего не публикуется')
    print('')
    print('| Причина | Запусков за 24 часа |')
    print('|---|---:|')
    for reason, count in top_items(d24['no_publish_reasons'], 10):
        print(f'| {reason_label(reason)} | {count} |')
    if not d24['no_publish_reasons']:
        print('| — | 0 |')
    print('')

    print('## Что блокирует добавление новых материалов')
    print('')
    print('| Причина | Запусков за 24 часа |')
    print('|---|---:|')
    for reason, count in top_items(d24['admission_blocks'], 10):
        print(f'| {block_label(reason)} | {count} |')
    if not d24['admission_blocks']:
        print('| — | 0 |')
    print('')

    print('## Предупреждения и диагностика')
    print('')
    if hard:
        for item in hard:
            print(f'- 🔴 **КРИТИЧНО:** {item}')
    if warnings:
        for item in warnings:
            print(f'- 🟡 **ВНИМАНИЕ:** {item}')
    if not hard and not warnings:
        print('- 🟢 Активных предупреждений нет.')
    print('')
    print('> Критические пороги предназначены для обнаружения технических инцидентов. Низкая доля добавления в очередь — диагностический сигнал, а не автоматическая ошибка системы.')
    print('')

    print('<details>')
    print('<summary>Последние 12 производственных запусков</summary>')
    print('')
    print('| Время UTC | Результат | Причина | Кандидаты | Добавлено | Опубликовано | Ошибки | AI |')
    print('|---|---|---|---:|---:|---:|---:|---|')
    for r in data[-12:]:
        a = r.get('admission', {})
        p = r.get('provider', {})
        result = RESULT_LABELS.get(r.get('business_result'), r.get('business_result', '-'))
        provider = PROVIDER_LABELS.get(p.get('used'), p.get('used') or '-')
        print(f"| {time.strftime('%m-%d %H:%M', time.gmtime(r.get('ts', 0)))} | {result} | {reason_label(r.get('business_reason', ''))} | {r.get('candidates', 0)} | {a.get('added', 0)} | {r.get('published', 0)} | {r.get('item_failures', 0)} | {provider} |")
    print('')
    print('</details>')


def evaluate(data, d24):
    hard = []
    warnings = []
    consecutive = 0
    for r in reversed(data):
        if r.get('business_result') == 'NO_PUBLISH':
            consecutive += 1
        else:
            break

    if ALERT_NO_PUBLISH_RUNS and consecutive >= ALERT_NO_PUBLISH_RUNS:
        hard.append(f'подряд {consecutive} запусков без публикации (аварийный порог: {ALERT_NO_PUBLISH_RUNS})')

    if ALERT_PUBLISH_FAILURES_24H and d24['attempts'] >= MIN_RATE_SAMPLE_ATTEMPTS:
        if d24['failures'] >= ALERT_PUBLISH_FAILURES_24H and d24['failure_rate'] >= ALERT_PUBLISH_FAILURE_RATE:
            hard.append(f'ошибки публикации за 24 часа: {d24["failures"]} из {d24["attempts"]} ({d24["failure_rate"]:.1f}%), аварийный порог {ALERT_PUBLISH_FAILURE_RATE:.0f}%')
        elif d24['failures'] >= WARN_PUBLISH_FAILURES_24H and d24['failure_rate'] >= WARN_PUBLISH_FAILURE_RATE:
            warnings.append(f'ошибки публикации за 24 часа: {d24["failures"]} из {d24["attempts"]} ({d24["failure_rate"]:.1f}%), повышенный уровень, но ниже аварийного порога')

    if ALERT_RSS_ERROR_RATE and d24['rss_attempts'] >= MIN_RATE_SAMPLE_ATTEMPTS and d24['rss_error_rate'] >= ALERT_RSS_ERROR_RATE:
        hard.append(f'доля ошибок поисковых запросов RSS: {d24["rss_error_rate"]:.1f}% при аварийном пороге {ALERT_RSS_ERROR_RATE:.1f}%')

    latest = sums(data[-1:]) if data else sums([])
    if latest['candidates'] and latest['admission_added'] == 0:
        warnings.append('в последнем запуске были кандидаты, но ни один новый материал не попал в очередь')

    if d24['admission_candidates'] >= MIN_ADMISSION_SAMPLE and d24['admission_rate'] < WARN_ADMISSION_RATE:
        warnings.append(f'доля добавления в очередь за 24 часа {d24["admission_rate"]:.1f}% ниже диагностического ориентира {WARN_ADMISSION_RATE:.1f}%')

    if d24['direct_errors']:
        warnings.append(f'ошибки прямых RSS-лент за 24 часа: {d24["direct_errors"]}; требуется наблюдение источников')
    return hard, warnings


def check(state):
    data = rows(state)
    now = time.time()
    d24 = sums(window(data, 86400, now))
    hard, _warnings = evaluate(data, d24)
    if hard:
        print('КОНТРОЛЬ: КРИТИЧЕСКОЕ СОСТОЯНИЕ')
        for item in hard:
            print(' -', item)
        return 1
    print('КОНТРОЛЬ: НОРМА')
    return 0


def main():
    parser = argparse.ArgumentParser(description='Русский мониторинг Intily')
    parser.add_argument('--check', action='store_true', help='только проверка критических порогов')
    args = parser.parse_args()
    state = load()
    if args.check:
        raise SystemExit(check(state))
    print_dashboard(state)


if __name__ == '__main__':
    main()
