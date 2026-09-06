#!/usr/bin/env python3
"""Русская аналитика текущего запуска Intily AI News Publisher.

Парсит только stdout текущего запуска publisher. Никаких дополнительных запросов
к RSS/AI/Telegram не делает. Сохраняет компактную историю поисковых запросов и
прямых источников для Intily Production Monitor.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

LOG_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/tmp/intily-publisher.log')
STATE_PATH = Path('data/intily-query-intelligence.json')
HISTORY_LIMIT = 100

QUERY_RE = re.compile(r'^RSS_QUERY\s+(WORLD|RUSSIA)\s+raw\s+(\d+)\s+(.+)$')
DIRECT_RE = re.compile(r'^RSS_DIRECT\s+(.+?)\s+raw\s+(\d+)$')
ERROR_RE = re.compile(r'^FEED_ERROR\s+(.+)$')
SUMMARY_RE = re.compile(r'^INGEST_SUMMARY\s+raw\s+(\d+)\s+all\s+(\d+)\s+score_filtered\s+(\d+)\s+quality_filtered\s+(\d+)\s+story_dedup\s+(\d+)\s+candidates\s+(\d+)')
ADMISSION_RE = re.compile(r'^QUEUE_ADMISSION\s+(\{.*\})$')


def load_state():
    if not STATE_PATH.exists():
        return {'runs': []}
    try:
        data = json.loads(STATE_PATH.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or not isinstance(data.get('runs'), list):
            return {'runs': []}
        return data
    except Exception:
        return {'runs': []}


def parse():
    queries = []
    direct = []
    errors = []
    summary = {}
    admission = {}
    for raw_line in LOG_PATH.read_text(encoding='utf-8', errors='replace').splitlines() if LOG_PATH.exists() else []:
        line = raw_line.strip()
        m = QUERY_RE.match(line)
        if m:
            region, raw, query = m.groups()
            queries.append({'region': region, 'query': query, 'raw': int(raw)})
            continue
        m = DIRECT_RE.match(line)
        if m:
            source, raw = m.groups()
            direct.append({'source': source, 'raw': int(raw)})
            continue
        m = SUMMARY_RE.match(line)
        if m:
            keys = ('google_raw', 'all_items', 'score_filtered', 'quality_filtered', 'story_dedup', 'candidates')
            summary = dict(zip(keys, map(int, m.groups())))
            continue
        m = ADMISSION_RE.match(line)
        if m:
            try:
                admission = json.loads(m.group(1))
            except json.JSONDecodeError:
                admission = {}
            continue
        m = ERROR_RE.match(line)
        if m:
            errors.append(m.group(1)[:240])

    google_raw = sum(x['raw'] for x in queries)
    for x in queries:
        x['доля_поиска'] = round(x['raw'] / max(1, google_raw) * 100, 1)
    queries.sort(key=lambda x: (-x['raw'], x['region'], x['query']))
    direct.sort(key=lambda x: (-x['raw'], x['source']))
    return queries, direct, errors, summary, admission


def save(queries, direct, errors, summary, admission):
    state = load_state()
    run = {
        'ts': int(time.time()),
        'queries': queries,
        'direct': direct,
        'errors': errors,
        'summary': summary,
        'admission': admission,
    }
    state['runs'].append(run)
    state['runs'] = state['runs'][-HISTORY_LIMIT:]
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    return run, state


def print_current(run):
    q = run['queries']
    direct = run['direct']
    summary = run['summary']
    admission = run['admission']
    print('## Интеллект поиска — текущий автозапуск')
    print('')
    print('> Этот блок показывает именно текущий запуск Publisher. Он не подменяет историческую аналитику и не делает дополнительных запросов к источникам.')
    print('')
    print('### Что произошло с потоком новостей')
    print('')
    print('| Этап | Количество | Что означает |')
    print('|---|---:|---|')
    print(f"| Материалы из Google News | {summary.get('google_raw', sum(x['raw'] for x in q))} | свежие элементы, полученные поисковыми запросами |")
    print(f"| Материалы из прямых RSS | {sum(x['raw'] for x in direct)} | свежие элементы издательских лент |")
    print(f"| Отсеяно по математическому score | {summary.get('score_filtered', 0)} | ниже порога важности |")
    print(f"| Отсеяно по качеству/AI-релевантности | {summary.get('quality_filtered', 0)} | не соответствуют редакционной планке |")
    print(f"| Повторы одной истории | {summary.get('story_dedup', 0)} | разные публикации об одном событии |")
    print(f"| Кандидаты после discovery | {summary.get('candidates', 0)} | реально прошли discovery-фильтры |")
    print(f"| Добавлено в очередь | {admission.get('added', 0)} | новые истории после durable dedup |")
    print('')
    print('### Поисковые запросы: где система действительно получает материал')
    print('')
    print('| Регион | Запрос | Свежих материалов | Доля поиска |')
    print('|---|---|---:|---:|')
    for x in q[:15]:
        print(f"| {x['region']} | {x['query']} | {x['raw']} | {x['доля_поиска']:.1f}% |")
    if len(q) > 15:
        print(f'| … | ещё {len(q) - 15} запросов | — | — |')
    if not q:
        print('| — | Данные текущего запуска отсутствуют | 0 | — |')
    print('')
    print('### Прямые источники')
    print('')
    print('| Источник | Свежих материалов |')
    print('|---|---:|')
    for x in direct:
        print(f"| {x['source']} | {x['raw']} |")
    if not direct:
        print('| — | 0 |')
    print('')
    print('### Что важно сейчас')
    print('')
    if admission.get('added', 0) == 0 and summary.get('candidates', 0):
        print(f"- ⚠️ **Поиск работает:** найдено {summary.get('candidates', 0)} кандидатов, но в очередь не добавлено ни одной новой истории.")
        print(f"- Главная причина admission: **{admission.get('dominant_block', 'не определена')}**.")
    elif admission.get('added', 0):
        print(f"- 🟢 В этом запуске в очередь добавлено **{admission.get('added', 0)}** новых историй.")
    else:
        print('- 🟡 В этом запуске новых кандидатов после discovery не получено; смотри таблицу запросов и ошибки источников.')
    if errors:
        print(f"- ⚠️ Ошибок источников: **{len(errors)}**.")
    else:
        print('- 🟢 Ошибок источников в текущем запуске не зафиксировано.')
    print('')


def main():
    queries, direct, errors, summary, admission = parse()
    run, _state = save(queries, direct, errors, summary, admission)
    print_current(run)


if __name__ == '__main__':
    main()
