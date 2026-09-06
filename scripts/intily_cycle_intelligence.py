#!/usr/bin/env python3
"""Русская аналитика текущего запуска Intily AI News Publisher.

Парсит stdout текущего запуска publisher. Никаких дополнительных запросов к
RSS/AI/Telegram не делает. Сохраняет компактную историю поисковых запросов,
источников и распределения весов для Intily Production Monitor.
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
SCORE_RE = re.compile(r'^SCORE_BUCKETS\s+(\{.*\})$')
ADMISSION_RE = re.compile(r'^QUEUE_ADMISSION\s+(\{.*\})$')
RESULT_RE = re.compile(r'^BUSINESS_RESULT\s+(\S+)(?:\s+(.+))?$')
COMPLETE_RE = re.compile(r'^RUN_COMPLETE\s+searched\s+(\S+)\s+candidates\s+(\d+)\s+published\s+(\d+)\s+queue\s+(\d+)$')
WAIT_RE = re.compile(r'^PUBLISH_WAIT\s+(\d+)$')

RESULT_LABELS = {
    'PUBLISHED': 'ОПУБЛИКОВАНО',
    'NO_PUBLISH': 'НЕ ОПУБЛИКОВАНО',
    'PUBLISH_FAILED': 'ОШИБКА ПУБЛИКАЦИИ',
}

REASON_LABELS = {
    'telegram_delivery_ok': 'публикация в Telegram выполнена',
    'empty_queue_after_filters': 'после отбора очередь пуста',
    'publish_interval_not_reached': 'интервал между публикациями ещё не истёк; новость не считается опубликованной и остаётся в очереди',
    'admission_blocked_published_key': 'кандидаты уже были опубликованы ранее',
    'admission_blocked_candidate_count': 'новых кандидатов недостаточно для добавления',
    'no_candidates_and_empty_queue': 'нет новых кандидатов и очередь пуста',
}

BLOCK_LABELS = {
    'published_key': 'история уже опубликована',
    'known_recent': 'материал недавно уже обрабатывался',
    'already_queued': 'материал уже в очереди',
    'story_queue': 'та же история уже в очереди',
    'story_history': 'та же история уже была опубликована недавно',
    'none': 'нет блокировки',
}


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
    score_buckets = {}
    admission = {}
    result = {}
    complete = {}
    wait_seconds = None
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
        m = SCORE_RE.match(line)
        if m:
            try:
                score_buckets = json.loads(m.group(1))
            except json.JSONDecodeError:
                score_buckets = {}
            continue
        m = ADMISSION_RE.match(line)
        if m:
            try:
                admission = json.loads(m.group(1))
            except json.JSONDecodeError:
                admission = {}
            continue
        m = WAIT_RE.match(line)
        if m:
            wait_seconds = int(m.group(1))
            continue
        m = RESULT_RE.match(line)
        if m:
            result = {'code': m.group(1), 'reason': (m.group(2) or '').strip()}
            continue
        m = COMPLETE_RE.match(line)
        if m:
            searched, candidates, published, queue = m.groups()
            complete = {
                'searched': searched.lower() == 'true',
                'candidates': int(candidates),
                'published': int(published),
                'queue': int(queue),
            }
            continue
        m = ERROR_RE.match(line)
        if m:
            errors.append(m.group(1)[:240])

    google_raw = sum(x['raw'] for x in queries)
    for x in queries:
        x['доля_поиска'] = round(x['raw'] / max(1, google_raw) * 100, 1)
    queries.sort(key=lambda x: (-x['raw'], x['region'], x['query']))
    direct.sort(key=lambda x: (-x['raw'], x['source']))
    return queries, direct, errors, summary, score_buckets, admission, result, complete, wait_seconds


def save(queries, direct, errors, summary, score_buckets, admission, result, complete, wait_seconds):
    state = load_state()
    run = {
        'ts': int(time.time()),
        'queries': queries,
        'direct': direct,
        'errors': errors,
        'summary': summary,
        'score_buckets': score_buckets,
        'admission': admission,
        'result': result,
        'complete': complete,
        'publish_wait_seconds': wait_seconds,
    }
    state['runs'].append(run)
    state['runs'] = state['runs'][-HISTORY_LIMIT:]
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    return run


def print_current(run):
    q = run['queries']
    direct = run['direct']
    errors = run['errors']
    summary = run['summary']
    score_buckets = run.get('score_buckets', {})
    admission = run['admission']
    result = run['result']
    complete = run['complete']
    wait_seconds = run.get('publish_wait_seconds')

    candidates = complete.get('candidates', summary.get('candidates', 0))
    published = complete.get('published', 0)
    queue = complete.get('queue', 0)
    result_code = result.get('code', '')

    print('## Аналитика текущего запуска')
    print('')
    print('> Здесь показано только то, что произошло в этом конкретном запуске Publisher. История за 24 часа и 7 дней находится в Intily Production Monitor.')
    print('')
    print('### Итог запуска')
    print('')
    print('| Показатель | Значение |')
    print('|---|---:|')
    print(f"| Результат | {RESULT_LABELS.get(result_code, result_code or 'не определён')} |")
    print(f"| Опубликовано в Telegram | {published} |")
    print(f"| Кандидатов после отбора | {candidates} |")
    print(f"| Новых материалов добавлено в очередь | {admission.get('added', 0)} |")
    print(f"| Материалов в очереди после запуска | {queue} |")
    if wait_seconds is not None:
        print(f"| Ожидание интервала публикации | {wait_seconds} сек. |")
    if result.get('reason'):
        print(f"| Причина результата | {REASON_LABELS.get(result['reason'], result['reason'])} |")
    print('')

    if score_buckets:
        print('### Распределение входных материалов по весу')
        print('')
        print('| Вес | Материалов |')
        print('|---:|---:|')
        for name in ('0–39', '40–49', '50–59', '60–69', '70–79', '80–84', '85–89', '90–100'):
            print(f"| {name} | {int(score_buckets.get(name, 0) or 0)} |")
        print('')

    print('### Что произошло с новостями')
    print('')
    print('| Этап | Количество | Что это означает |')
    print('|---|---:|---|')
    print(f"| Материалы из Google News | {summary.get('google_raw', sum(x['raw'] for x in q))} | получено поиском |")
    print(f"| Материалы из прямых RSS | {sum(x['raw'] for x in direct)} | получено напрямую из лент |")
    print(f"| Отсеяно по оценке важности | {summary.get('score_filtered', 0)} | ниже заданного порога |")
    print(f"| Отсеяно по качеству и релевантности | {summary.get('quality_filtered', 0)} | не соответствует редакционной планке |")
    print(f"| Повторы одной истории | {summary.get('story_dedup', 0)} | несколько публикаций об одном событии |")
    print(f"| Кандидаты после отбора | {candidates} | прошли первичный отбор |")
    print(f"| Новые материалы в очереди | {admission.get('added', 0)} | прошли защиту от повторов |")
    print('')

    print('### Поисковые запросы этого запуска')
    print('')
    print('| Регион | Запрос | Материалов | Доля |')
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
    print('| Источник | Материалов |')
    print('|---|---:|')
    for x in direct:
        print(f"| {x['source']} | {x['raw']} |")
    if not direct:
        print('| — | 0 |')
    print('')

    print('### Что важно сейчас')
    print('')
    if wait_seconds is not None and result.get('reason') == 'publish_interval_not_reached':
        print(f'- 🟡 **Публикация не выполнялась:** минимальный интервал ещё не истёк ({wait_seconds} сек.). Это **не означает, что новость опубликована**. Очередь и `published` не меняются из-за одного только ожидания.')
    if admission.get('added', 0) == 0 and candidates:
        block = BLOCK_LABELS.get(admission.get('dominant_block', ''), admission.get('dominant_block', 'не определена'))
        print(f"- ⚠️ **Поиск работает:** найдено {candidates} кандидатов, но новых материалов в очередь не добавлено.")
        print(f"- Основная причина: **{block}**.")
    elif admission.get('added', 0):
        print(f"- 🟢 В этом запуске в очередь добавлено **{admission.get('added', 0)}** новых материалов.")
    else:
        print('- 🟡 В этом запуске новых кандидатов после отбора не получено.')
    if errors:
        print(f"- ⚠️ Ошибок источников: **{len(errors)}**.")
    else:
        print('- 🟢 Ошибок источников в текущем запуске не зафиксировано.')
    print('')


def main():
    parsed = parse()
    run = save(*parsed)
    print_current(run)


if __name__ == '__main__':
    main()
