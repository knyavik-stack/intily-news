#!/usr/bin/env python3
"""Русская аналитика критериев отбора Intily.

Не делает сетевых запросов. Показывает причины отсева, каноническую формулу
веса, распределение входного потока и durable-очереди, а также причины нулевой
выдачи отдельных источников.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from intily_scoring_policy import THRESHOLD, WEIGHTS

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

    print('## Причины отсева — текущий запуск\n')
    print('| Этап | Количество | Доля от входа этапа | Что означает |')
    print('|---|---:|---:|---|')
    print(f'| Получено из источников | {raw} | 100% | материалы младше активного окна |')
    print(f'| Отсечено по весу | {score_filtered} | {pct(score_filtered, raw)} | итоговый вес ниже {THRESHOLD:.1f} |')
    print(f'| Отсечено по качеству/релевантности | {quality_filtered} | {pct(quality_filtered, max(1, raw-score_filtered))} | не прошёл AI relevance или редакционный gate |')
    print(f'| Схлопнуто как повтор истории | {story_dedup} | {pct(story_dedup, max(1, raw-score_filtered-quality_filtered))} | одно событие найдено в нескольких источниках/запросах |')
    print(f'| Кандидаты | {candidates} | — | прошли ingestion-фильтры |')
    print(f'| Не допущено в очередь | {max(0, candidates-added)} | {pct(max(0, candidates-added), max(1, candidates))} | уже опубликовано / недавно известно / в очереди / semantic history |')
    print(f'| Новых в очереди | {added} | {pct(added, max(1, candidates))} | реально допущены в durable queue |')
    print('\n### Причины admission\n')
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


def print_weight_policy():
    descriptions = {
        'relevance': 'прямое отношение материала к ИИ',
        'ai_specificity': 'плотность конкретных AI-концепций, моделей и технологий',
        'impact': 'масштаб и значимость события',
        'event_concreteness': 'наличие конкретного события: запуск, сделка, исследование, закон и т.п.',
        'practical_value': 'внедрение, автоматизация, разработка и применимость',
        'novelty': 'новизна, эксклюзивность и числовая конкретика',
        'source_quality': 'качество и доверенность источника',
        'evidence': 'информативность описания без линейной накрутки длиной',
        'freshness': 'свежесть материала в активном окне',
        'timeliness': 'дополнительная ценность действительно свежего события',
    }
    names = {
        'relevance': 'AI-релевантность',
        'ai_specificity': 'AI-специфичность',
        'impact': 'Влияние события',
        'event_concreteness': 'Конкретность события',
        'practical_value': 'Практическая ценность',
        'novelty': 'Новизна',
        'source_quality': 'Качество источника',
        'evidence': 'Доказательность',
        'freshness': 'Свежесть',
        'timeliness': 'Своевременность',
    }
    print('## Как формируется вес новости\n')
    print('Вес — детерминированная математическая оценка **0–100** с точностью до одного знака. Порог остаётся **60.0**. Мы не снижаем порог ради количества: расширяем шкалу за счёт независимых оценочных измерений.')
    print('\n| Компонент | Максимум | Что оценивается |')
    print('|---|---:|---|')
    for key, maximum in WEIGHTS.items():
        print(f'| {names[key]} | {maximum:.1f} | {descriptions[key]} |')
    print('| Низкий сигнал | −6.0 | реклама, sponsored, промокоды и аналогичный шум |')
    print('\n### Логика калибровки\n')
    print('- Порог **60.0 не меняется**: это редакционная граница допуска.')
    print('- Старая проблема была не в самом пороге, а в том, что большая часть потенциально полезного балла была недоступна реальным RSS-материалам.')
    print('- AI-релевантность отделена от AI-специфичности: «материал про AI» и «материал с конкретным технологическим событием» — разные свойства.')
    print('- Добавлена конкретность события: запуск, релиз, исследование, инвестиция, сделка, регулирование и другие проверяемые события получают отдельный вклад.')
    print('- Свежесть разделена на общий freshness и timeliness, чтобы текущие события не конкурировали на равных со старыми материалами.')
    print('- Случайный бонус региона не используется. География влияет только на publication priority.')
    print('\n### Категории\n')
    print('| Вес | Категория |')
    print('|---:|---|')
    print(f'| 0–{THRESHOLD-0.1:.1f} | не проходит порог |')
    print(f'| {THRESHOLD:.1f}–84.9 | A |')
    print('| 85.0–100 | S |')


def print_weight_distribution(state):
    run = current_run(state)
    rss = run.get('rss', {})
    incoming = rss.get('score_buckets', {})
    queue = state.get('queue', [])
    queue_counts = Counter(bucket(x.get('importance', x.get('score'))) for x in queue)
    names = ('0–39', '40–49', '50–59', '60–69', '70–79', '80–84', '85–89', '90–100')
    print('\n## Распределение новостей по весу\n')
    print('### Входной поток последнего запуска\n')
    print('| Вес | Материалов |')
    print('|---:|---:|')
    for name in names:
        print(f"| {name} | {int(incoming.get(name, 0) or 0)} |")
    print('\n### Durable-очередь сейчас\n')
    print('| Вес | Новостей |')
    print('|---:|---:|')
    if queue_counts:
        for name in names:
            if queue_counts.get(name, 0):
                print(f'| {name} | {queue_counts[name]} |')
    else:
        print('| — | 0 |')


def print_sources(search):
    runs = search.get('runs', []) if isinstance(search, dict) else []
    latest = runs[-1] if runs else {}
    print('\n## Почему источник может не дать материал\n')
    print('**Нулевой результат сам по себе не является ошибкой.** Он означает, что запрос/лента ответили, но в активном временном окне не осталось свежих материалов. Ошибка — отдельный технический сигнал.')
    print('\n| Источник/запрос | Результат | Интерпретация |')
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
        print('\n### Ошибки источников текущего запуска')
        for error in errors:
            print(f'- {error}')
    print('\nМатериал также может исчезнуть после получения: из-за низкого веса, нерелевантности ИИ, повторения той же истории, уже опубликованного ключа, недавней обработки или наличия аналогичной истории в очереди/semantic memory.')


def main():
    state = load_json(STATE_PATH, {})
    search = load_json(SEARCH_PATH, {'runs': []})
    run = current_run(state)
    print('# Intily — аналитика алгоритма отбора\n')
    print_rejection(run)
    print_weight_policy()
    print_weight_distribution(state)
    print_sources(search)


if __name__ == '__main__':
    main()
