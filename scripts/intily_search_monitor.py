#!/usr/bin/env python3
"""Русская историческая аналитика поискового потока для Intily Production Monitor."""
from __future__ import annotations

import json
import time
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parents[1] / 'data' / 'intily-query-intelligence.json'


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
    google_raw = direct_raw = 0
    errors = 0
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
    return launches, google_raw, direct_raw, errors, queries, sources


def print_section(runs):
    print('## Поисковая аналитика — история')
    print('')
    if not runs:
        print('Пока нет сохранённой истории поисковых запусков. Она появится после первого нового запуска Publisher.')
        return

    d24 = aggregate(window(runs, 86400))
    d7 = aggregate(window(runs, 7 * 86400))
    stored = aggregate(runs)
    print('> Здесь показана накопленная статистика поисковых запусков. Дополнительных обращений к источникам нет.')
    print('')
    print('| Показатель | 24 часа | 7 дней | Сохранённая история |')
    print('|---|---:|---:|---:|')
    print(f'| Запусков | {d24[0]} | {d7[0]} | {stored[0]} |')
    print(f'| Материалов из Google News | {d24[1]} | {d7[1]} | {stored[1]} |')
    print(f'| Материалов из прямых RSS | {d24[2]} | {d7[2]} | {stored[2]} |')
    print(f'| Ошибок источников | {d24[3]} | {d7[3]} | {stored[3]} |')
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
    print('### Последний запуск Publisher')
    print('')
    print(f"- Материалов из Google News: **{latest_summary.get('google_raw', 0)}**")
    print(f"- Кандидатов после отбора: **{latest_summary.get('candidates', 0)}**")
    print(f"- Добавлено в очередь: **{latest_admission.get('added', 0)}**")
    print(f"- Основная причина отказа: **{latest_admission.get('dominant_block', 'не определена')}**")
    if result.get('code'):
        print(f"- Результат: **{result.get('code')}**")
    print('')

    print('### Как правильно читать эти данные')
    print('')
    print('- Большое количество полученных материалов ещё не означает высокий редакционный результат: один запрос может многократно возвращать одну и ту же историю.')
    print('- Нулевой результат одного источника не означает, что источник плохой; решение принимается по устойчивому тренду за несколько запусков.')
    print('- Сейчас статистика показывает, **откуда приходит материал**, но не приписывает публикацию конкретному запросу: один материал может прийти по нескольким запросам.')
    print('- Поэтому система пока не рассчитывает искусственный рейтинг эффективности запросов.')
    print('- Следующий безопасный шаг — добавить уникальный идентификатор происхождения материала и только после этого считать путь «запрос → кандидат → очередь → публикация».')


if __name__ == '__main__':
    print_section(load())
