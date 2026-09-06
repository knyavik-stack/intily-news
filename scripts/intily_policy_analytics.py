#!/usr/bin/env python3
"""Русская аналитика критериев отбора Intily.

Не делает сетевых запросов. Показывает причины отсева, действующую формулу
веса, распределение весов входного потока и durable-очереди, а также причины
нулевой выдачи отдельных источников.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / 'data' / 'intily-ai-news-state.json'
SEARCH_PATH = ROOT / 'data' / 'intily-query-intelligence.json'


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def pct(value, total):
    return f'{value / max(1, total) * 100:.1f}%'


def bucket(score):
    try:
        value = float(score)
    except (TypeError, ValueError):
        return 'не определён'
    if value < 40:
        return '0–39'
    if value < 50:
        return '40–49'
    if value < 60:
        return '50–59'
    if value < 70:
        return '60–69'
    if value < 80:
        return '70–79'
    if value < 85:
        return '80–84'
    if value < 90:
        return '85–89'
    return '90–100'


def current_run(state):
    rows = state.get('run_history', [])
    return rows[-1] if rows else {}


def print_rejection(run):
    rss = run.get('rss', {})
    admission = run.get('admission', {})
    raw = int(rss.get('raw_items', 0) or 0)
    score_filtered = int(rss.get('score_filtered', 0) or 0)
    quality_filtered = int(rss.get('quality_filtered', 0) or 0)
    story_dedup = int(rss.get('story_dedup', 0) or 0)
    candidates = int(rss.get('candidates', 0) or 0)
    added = int(admission.get('added', 0) or 0)

    print('## Причины отсева — текущий запуск')
    print('')
    print('| Этап | Количество | Доля от входа этапа | Что означает |')
    print('|---|---:|---:|---|')
    print(f'| Получено из источников | {raw} | 100% | материалы младше активного окна |')
    print(f'| Отсечено по весу | {score_filtered} | {pct(score_filtered, raw)} | итоговый вес ниже 60 |')
    print(f'| Отсечено по качеству/релевантности | {quality_filtered} | {pct(quality_filtered, max(1, raw-score_filtered))} | не прошёл AI relevance или редакционный gate |')
    print(f'| Схлопнуто как повтор истории | {story_dedup} | {pct(story_dedup, max(1, raw-score_filtered-quality_filtered))} | одно событие найдено в нескольких источниках/запросах |')
    print(f'| Кандидаты | {candidates} | — | прошли ingestion-фильтры |')
    print(f'| Не допущено в очередь | {max(0, candidates-added)} | {pct(max(0, candidates-added), max(1, candidates))} | уже опубликовано / недавно известно / в очереди / semantic history |')
    print(f'| Новых в очереди | {added} | {pct(added, max(1, candidates))} | реально допущены в durable queue |')
    print('')
    print('### Причины admission')
    print('')
    labels = {
        'published_key': 'уже опубликовано ранее',
        'known_recent': 'недавно уже обрабатывалось',
        'already_queued': 'уже находится в очереди',
        'story_queue': 'та же история уже находится в очереди',
        'story_history': 'та же история уже была опубликована недавно',
    }
    print('| Причина | Количество |')
    print('|---|---:|')
    for key, label in labels.items():
        print(f"| {label} | {int(admission.get(key, 0) or 0)} |")
    print('')


def print_weight_policy():
    print('## Как формируется вес новости')
    print('')
    print('Вес — детерминированная математическая оценка **0–100** с точностью до одного знака после запятой. География не входит в вес: RUSSIA/WORLD балансируется отдельно на этапе публикации.')
    print('')
    print('| Компонент | Максимум | Что оценивается |')
    print('|---|---:|---|')
    print('| AI-релевантность | 25 | прямое отношение к ИИ, LLM, нейросетям, агентам, роботам и AI-инфраструктуре |')
    print('| Влияние события | 18 | запуск, новая модель, прорыв, инвестиции, безопасность, закон, крупная сделка и другие признаки значимого события |')
    print('| Практическая ценность | 15 | внедрение, автоматизация, разработка, инструменты, инфраструктура, бизнес-кейсы и применимость |')
    print('| Новизна/конкретность | 12 | эксклюзивность, «впервые», крупные/рекордные события и числовая конкретика |')
    print('| Качество источника | 10 | приоритетный источник 10; доверенный 7; прочий 4 |')
    print('| Доказательность | 8 | информативность описания; длинное описание не получает линейного неограниченного бонуса |')
    print('| Свежесть | 7 | непрерывное снижение от 7.0 к 0.0 за 12 часов, без грубых ступеней |')
    print('| Значимость риска/проблемы | 5 | уязвимость, сбой, утечка, безопасность, риск и другие существенные проблемы |')
    print('| Низкий сигнал | −8 | реклама, sponsored, промокоды, гороскопы и т.п. |')
    print('')
    print('**Порог допуска: 60.0.** Балл ниже порога не попадает в очередь.')
    print('')
    print('### Почему один знак после запятой не означает искусственную уникальность')
    print('')
    print('Свежесть и доказательность теперь считаются непрерывно, поэтому 60.1 и 60.2 имеют реальный смысл. Если две новости действительно имеют одинаковую оценку, система не «подделывает» разницу случайным шумом: они остаются равными по весу, а порядок разрешается детерминированными признаками времени и редакционной ценности.')
    print('')
    print('### Категории')
    print('')
    print('| Вес | Категория |')
    print('|---:|---|')
    print('| 0–59.9 | не проходит порог |')
    print('| 60.0–84.9 | A |')
    print('| 85.0–100 | S |')
    print('')


def print_weight_distribution(state):
    run = current_run(state)
    rss = run.get('rss', {})
    incoming = rss.get('score_buckets', {})
    queue = state.get('queue', [])
    queue_counts = Counter(bucket(x.get('importance', x.get('score'))) for x in queue)
    names = ('0–39', '40–49', '50–59', '60–69', '70–79', '80–84', '85–89', '90–100')

    print('## Распределение новостей по весу')
    print('')
    print('### Входной поток последнего запуска')
    print('')
    if incoming:
        print('| Вес | Материалов |')
        print('|---:|---:|')
        for name in names:
            print(f"| {name} | {int(incoming.get(name, 0) or 0)} |")
    else:
        print('Данные распределения входного потока появятся после первого запуска с новой telemetry policy.')
    print('')
    print('### Durable-очередь сейчас')
    print('')
    print('| Вес | Новостей |')
    print('|---:|---:|')
    for name in names:
        if queue_counts.get(name, 0):
            print(f'| {name} | {queue_counts[name]} |')
    if not queue:
        print('| — | 0 |')
    print('')


def print_sources(search):
    runs = search.get('runs', []) if isinstance(search, dict) else []
    latest = runs[-1] if runs else {}
    print('## Почему источник может не дать материал')
    print('')
    print('**Нулевой результат сам по себе не является ошибкой.** Он означает, что запрос/лента ответили, но в активном временном окне не осталось свежих материалов. Ошибка — отдельный технический сигнал.')
    print('')
    print('| Источник/запрос | Результат | Интерпретация |')
    print('|---|---:|---|')
    for q in latest.get('queries', []):
        raw = int(q.get('raw', 0) or 0)
        reason = 'есть свежие материалы' if raw else 'ответил, но свежих материалов в окне нет'
        print(f"| {q.get('region','')} — {q.get('query','')} | {raw} | {reason} |")
    for src in latest.get('direct', []):
        raw = int(src.get('raw', 0) or 0)
        reason = 'есть свежие материалы' if raw else 'лента доступна, но свежих материалов в окне нет'
        print(f"| {src.get('source','')} | {raw} | {reason} |")
    errors = latest.get('errors', [])
    if errors:
        print('')
        print('### Ошибки источников текущего запуска')
        for error in errors:
            print(f'- {error}')
    print('')
    print('Материал также может исчезнуть после получения: из-за низкого веса, нерелевантности ИИ, повторения той же истории, уже опубликованного ключа, недавней обработки или наличия аналогичной истории в очереди/semantic memory.')
    print('')


def main():
    state = load_json(STATE_PATH, {})
    search = load_json(SEARCH_PATH, {'runs': []})
    run = current_run(state)
    print('# Intily — аналитика алгоритма отбора')
    print('')
    print_rejection(run)
    print_weight_policy()
    print_weight_distribution(state)
    print_sources(search)


if __name__ == '__main__':
    main()
