#!/usr/bin/env python3
"""Русская историческая аналитика поискового и весового потока Intily."""
from __future__ import annotations

import json
import time
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parents[1] / 'data' / 'intily-query-intelligence.json'

RESULT_LABELS = {
    'PUBLISHED': 'ОПУБЛИКОВАНО',
    'NO_PUBLISH': 'НЕ ОПУБЛИКОВАНО',
    'PUBLISH_FAILED': 'ОШИБКА ПУБЛИКАЦИИ',
}

BLOCK_LABELS = {
    'published_key': 'уже опубликовано ранее',
    'known_recent': 'недавно уже обрабатывалось',
    'already_queued': 'уже находится в очереди',
    'story_queue': 'та же история уже находится в очереди',
    'story_history': 'та же история уже была опубликована недавно',
    'none': 'нет блокировки',
}

BUCKETS = ('0–39', '40–49', '50–59', '60–69', '70–79', '80–84', '85–89', '90–100')


def load():
    if not STATE_PATH.exists():
        return []
    try:
        data = json.loads(STATE_PATH.read_text(encoding='utf-8'))
        return data.get('runs', []) if isinstance(data, dict) else []
    except Exception:
        return []


def window(runs, seconds):
    now = time.time()
    return [r for r in runs if now - float(r.get('ts', 0) or 0) <= seconds]


def aggregate(runs):
    queries = {}
    sources = {}
    buckets = {name: 0 for name in BUCKETS}
    google_raw = direct_raw = errors = score_total = 0
    launches = len(runs)
    for r in runs:
        for q in r.get('queries', []):
            key = (q.get('region', ''), q.get('query', ''))
            queries[key] = queries.get(key, 0) + int(q.get('raw', 0) or 0)
            google_raw += int(q.get('raw', 0) or 0)
        for s in r.get('direct', []):
            name = s.get('source', '')
            sources[name] = sources.get(name, 0) + int(s.get('raw', 0) or 0)
            direct_raw += int(s.get('raw', 0) or 0)
        errors += len(r.get('errors', []))
        for name in BUCKETS:
            buckets[name] += int(r.get('score_buckets', {}).get(name, 0) or 0)
    return launches, google_raw, direct_raw, errors, queries, sources, buckets


def print_section(runs):
    print('## Поисковая и весовая аналитика — история')
    print('')
    if not runs:
        print('Пока нет сохранённой истории поисковых запусков. Она появится после первого нового запуска издателя новостей.')
        return

    d24 = aggregate(window(runs, 86400))
    d7 = aggregate(window(runs, 7 * 86400))
    stored = aggregate(runs)
    print('> Здесь показана накопленная статистика поисковых и весовых запусков. Дополнительных обращений к источникам нет.')
    print('')
    print('| Показатель | 24 часа | 7 дней | Сохранённая история |')
    print('|---|---:|---:|---:|')
    print(f'| Запусков | {d24[0]} | {d7[0]} | {stored[0]} |')
    print(f'| Материалов из Google News | {d24[1]} | {d7[1]} | {stored[1]} |')
    print(f'| Материалов из прямых RSS | {d24[2]} | {d7[2]} | {stored[2]} |')
    print(f'| Ошибок источников | {d24[3]} | {d7[3]} | {stored[3]} |')
    print('')

    print('### Распределение входного потока по весу')
    print('')
    print('| Вес | 24 часа | 7 дней | История |')
    print('|---:|---:|---:|---:|')
    for i, name in enumerate(BUCKETS):
        print(f'| {name} | {d24[6][name]} | {d7[6][name]} | {stored[6][name]} |')
    print('')

    print('### Какие поисковые запросы чаще всего дают материал')
    print('')
    print('| Регион | Запрос | Материалов |')
    print('|---|---|---:|')
    for (region, query), count in sorted(d24[4].items(), key=lambda x: (-x[1], x[0]))[:12]:
        print(f'| {region} | {query} | {count} |')
    if not d24[4]:
        print('| — | Пока нет данных | 0 |')
    print('')

    print('### Какие прямые источники чаще всего дают материал')
    print('')
    print('| Источник | Материалов |')
    print('|---|---:|')
    for source, count in sorted(d24[5].items(), key=lambda x: (-x[1], x[0]))[:10]:
        print(f'| {source} | {count} |')
    if not d24[5]:
        print('| — | 0 |')
    print('')

    latest = runs[-1]
    latest_summary = latest.get('summary', {})
    latest_admission = latest.get('admission', {})
    result = latest.get('result', {})
    wait = latest.get('publish_wait_seconds')
    print('### Последний запуск издателя новостей')
    print('')
    print(f"- Материалов из Google News: **{latest_summary.get('google_raw', 0)}**")
    print(f"- Кандидатов после отбора: **{latest_summary.get('candidates', 0)}**")
    print(f"- Добавлено в очередь: **{latest_admission.get('added', 0)}**")
    block = latest_admission.get('dominant_block', 'не определена')
    print(f"- Основная причина отказа: **{BLOCK_LABELS.get(block, block)}**")
    if wait is not None:
        print(f"- Интервал публикации: ожидалось ещё **{wait} сек.**; это не публикация и не удаление новости из очереди.")
    if result.get('code'):
        print(f"- Результат: **{RESULT_LABELS.get(result.get('code'), result.get('code'))}**")
    print('')

    print('### Как правильно читать эти данные')
    print('')
    print('- Большой входной поток ещё не означает высокий редакционный результат: один материал может приходить из нескольких запросов и источников.')
    print('- Вес теперь детерминирован и считается с одним знаком после запятой; география не искажает саму редакционную оценку.')
    print('- Нулевой результат одного источника не означает, что источник плохой: сначала проверяется доступность, затем устойчивый yield за несколько запусков.')
    print('- Сейчас запросы показывают объём найденного материала, а не гарантированное число уникальных публикаций: один материал может прийти по нескольким запросам.')
    print('- Следующая эволюция — provenance конкретного материала, чтобы честно считать путь «запрос → уникальная история → кандидат → очередь → публикация».')


if __name__ == '__main__':
    print_section(load())
