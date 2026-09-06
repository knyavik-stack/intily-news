#!/usr/bin/env python3
"""Русская аналитика критериев отбора Intily.

Не делает сетевых запросов. Использует сохранённый state, историю поисковой
аналитики и сам код publisher как источник действующей policy. Показывает
причины отсева, формулу веса, состояние источников и распределение весов в
текущей durable-очереди.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / 'data' / 'intily-ai-news-state.json'
SEARCH_PATH = ROOT / 'data' / 'intily-query-intelligence.json'
PUBLISHER_PATH = ROOT / 'scripts' / 'intily_ai_news.py'


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


def policy_values():
    text = PUBLISHER_PATH.read_text(encoding='utf-8', errors='replace') if PUBLISHER_PATH.exists() else ''
    values = {}
    patterns = {
        'lookback_hours': r"LOOKBACK\s*=\s*timedelta\(hours=(\d+)\)",
        'importance_threshold': r"IMPORTANCE_THRESHOLD\s*=\s*([0-9.]+)",
        'publish_interval_seconds': r"PUBLISH_INTERVAL_SECONDS\s*=\s*([^\n]+)",
        'known_minutes': r"KNOWN_LOOKBACK_SECONDS\s*=\s*90\s*\*\s*60",
        'story_lookback': r"STORY_LOOKBACK_SECONDS\s*=\s*(\d+)\s*\*\s*3600",
        'russia_bonus': r"RUSSIA_WEIGHT_BONUS_MIN\s*=\s*([0-9.]+).*?RUSSIA_WEIGHT_BONUS_MAX\s*=\s*([0-9.]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.S)
        if match:
            values[key] = match.groups()
    return values


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
    print(f'| Получено из источников | {raw} | 100% | материалы младше установленного окна |')
    print(f'| Отсечено по весу | {score_filtered} | {pct(score_filtered, raw)} | итоговый вес ниже 60 |')
    print(f'| Отсечено по AI-релевантности | {quality_filtered} | {pct(quality_filtered, max(1, raw-score_filtered))} | материал не прошёл явный AI relevance gate |')
    print(f'| Схлопнуто как повтор одной истории | {story_dedup} | {pct(story_dedup, max(1, raw-score_filtered-quality_filtered))} | та же история уже представлена другим материалом |')
    print(f'| Кандидаты | {candidates} | — | прошли ingestion-фильтры |')
    print(f'| Не допущено в очередь | {max(0, candidates-added)} | {pct(max(0, candidates-added), max(1, candidates))} | опубликовано ранее / известно / в очереди / semantic history |')
    print(f'| Новых в очереди | {added} | {pct(added, max(1, candidates))} | реально допущены durable admission |')
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
    values = policy_values()
    threshold = values.get('importance_threshold', ('60.0',))[0]
    bonus = values.get('russia_bonus', ('2.0', '5.0'))
    print('## Как формируется вес новости')
    print('')
    print('Вес — математическая оценка **0–100**. Он не является вероятностью публикации и не означает «качество текста».')
    print('')
    print('| Компонент | Вклад | Критерий |')
    print('|---|---:|---|')
    print('| AI-релевантность | +45 | материал явно относится к ИИ/LLM/нейросетям/агентам/роботам и т.п. |')
    print('| Влияние события | до +20 | запуск, модель, агент, прорыв, инвестиции, безопасность, закон и другие high-impact признаки |')
    print('| Практическое применение | до +15 | бизнес, автоматизация, разработка, внедрение, инструменты, инфраструктура и т.п. |')
    print('| Качество источника | +5 / +6 / +8 | обычный / доверенный / приоритетный источник |')
    print('| Свежесть | +4…+15 | чем новее материал, тем выше вклад |')
    print('| Региональная свежесть | −2…+3.5 | отдельная поправка для WORLD/RUSSIA и возраста |')
    print(f'| Россия: дополнительная поправка | +{bonus[0]}…+{bonus[1]} | применяется только к RUSSIA |')
    print('| Низкосигнальные признаки | −15 | реклама, sponsored, промокоды, гороскопы и т.п. |')
    print('')
    print(f'**Порог допуска по весу: {threshold}.** Ниже него материал отбрасывается до очереди.')
    print('')
    print('### Второй редакционный фильтр')
    print('')
    print('После веса дополнительно считается редакционная ценность: источник +3, high-impact +3, application +2, практическое внедрение +3, риск/проблема +3, эксклюзивность +2, информативное описание +1; короткое описание −3, низкосигнальный материал −8. Этот показатель используется при приоритизации очереди и не заменяет порог веса.')
    print('')
    print('### Категории веса')
    print('')
    print('| Вес | Категория |')
    print('|---:|---|')
    print('| 0–59 | не проходит порог |')
    print('| 60–84 | A |')
    print('| 85–100 | S |')
    print('')


def print_weight_distribution(state):
    queue = state.get('queue', [])
    counts = Counter(bucket(x.get('importance', x.get('score'))) for x in queue)
    print('## Распределение новостей по весу')
    print('')
    print('Ниже — **текущая durable-очередь после последнего запуска**. Это честная выборка, потому что веса всех отброшенных RSS-материалов исторически сейчас не сохраняются.')
    print('')
    print('| Вес | Новостей в очереди |')
    print('|---:|---:|')
    for name in ('0–39', '40–49', '50–59', '60–69', '70–79', '80–84', '85–89', '90–100', 'не определён'):
        if counts.get(name, 0):
            print(f'| {name} | {counts[name]} |')
    if not queue:
        print('| — | 0 |')
    print('')


def print_sources(search):
    runs = search.get('runs', []) if isinstance(search, dict) else []
    latest = runs[-1] if runs else {}
    print('## Почему источник может не дать материал')
    print('')
    print('**Это не всегда ошибка.** Нулевой результат означает: источник ответил, но за текущее окно свежих материалов не найдено. Ошибка означает, что запрос/лента не ответила нормально.')
    print('')
    print('| Источник/запрос | Последний результат | Интерпретация |')
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
    print('На практике ноль чаще всего означает одну из четырёх вещей: нет публикаций в заданном окне; Google News не поднял материал по формулировке запроса; материал старше 12 часов и отброшен; источник вернул материал, но он оказался нерелевантным/слишком слабым на следующих этапах.')
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
