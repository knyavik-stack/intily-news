#!/usr/bin/env python3
"""Историческая аналитика поискового потока для Intily Production Monitor."""
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
    print('> Эта секция не делает сетевых запросов. Она читает сохранённую телеметрию последних запусков Publisher.')
    print('')
    print('| Показатель | 24ч | 7д | Сохранено |')
    print('|---|---:|---:|---:|')
    print(f'| Запусков | {d24[0]} | {d7[0]} | {stored[0]} |')
    print(f'| Google News raw | {d24[1]} | {d7[1]} | {stored[1]} |')
    print(f'| Прямые RSS raw | {d24[2]} | {d7[2]} | {stored[2]} |')
    print(f'| Ошибки источников | {d24[3]} | {d7[3]} | {stored[3]} |')
    print('')

    print('### Самые результативные поисковые запросы по raw-yield')
    print('')
    print('| Регион | Запрос | Материалов |')
    print('|---|---|---:|')
    for (region, query), count in sorted(d24[4].items(), key=lambda x: (-x[1], x[0]))[:12]:
        print(f'| {region} | {query} | {count} |')
    if not d24[4]:
        print('| — | Пока нет данных | 0 |')
    print('')

    print('### Самые результативные прямые источники')
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
    print('### Последний запуск')
    print('')
    print(f"- Google News raw: **{latest_summary.get('google_raw', 0)}**")
    print(f"- Кандидаты: **{latest_summary.get('candidates', 0)}**")
    print(f"- Добавлено в очередь: **{latest_admission.get('added', 0)}**")
    print(f"- Главный блок admission: **{latest_admission.get('dominant_block', 'не определён')}**")
    print('')
    print('### Как это использовать')
    print('')
    print('- Большой raw-yield сам по себе **не означает** хороший источник: запрос может возвращать много повторов.')
    print('- Источник с нулевым yield в одном запуске не считается плохим; решение требует повторяющегося тренда.')
    print('- Нельзя распределять admission между запросами без provenance `query_id`: один материал может попасть в несколько запросов.')
    print('- После накопления истории можно безопасно вводить efficiency score и перераспределять поисковой бюджет.')


if __name__ == '__main__':
    print_section(load())
