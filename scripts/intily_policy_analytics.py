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

from intily_scoring_policy import THRESHOLD, WEIGHTS, BASE_MAX, AI_MAX
from intily_audience_policy import FINAL_THRESHOLD, PRE_AI_THRESHOLD

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
    except Exception:
        value = 0.0
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


def main():
    state = load_json(STATE_PATH, {})
    history = state.get('run_history', []) or []
    queue = state.get('queue', []) or []
    latest = history[-1] if history else {}
    admission = latest.get('admission', {}) or {}
    rss = latest.get('rss', {}) or {}

    scores = [float(x.get('importance', x.get('score', 0)) or 0) for x in queue]
    buckets = Counter(bucket(x) for x in scores)
    final_scores = [float(x.get('importance', x.get('score', 0)) or 0) for x in queue if x.get('score_stage') == 'final']
    pre_ai_scores = [float(x.get('importance', x.get('score', 0)) or 0) for x in queue if x.get('score_stage', 'pre_ai') != 'final']

    print('# Intily — аналитика политики отбора')
    print()
    print('## Каноническая формула')
    print()
    print(f'- Base score: **0–{BASE_MAX:g}**.')
    print(f'- AI audience contribution: **+3…+{AI_MAX:g}**.')
    print(f'- Final score: `min(100, base_score + audience_score × 3)`.')
    print(f'- Pre-AI gate: **{PRE_AI_THRESHOLD:g}**.')
    print(f'- Final publication gate: **{FINAL_THRESHOLD:g}**.')
    print(f'- `sum(WEIGHTS) = {sum(WEIGHTS.values()):g}`; canonical base ceiling = **{BASE_MAX:g}**.')
    print('- Queue/publication order: **final score descending**, freshness only as tie-breaker.')
    print('- Geography is not added to the mathematical score.')
    print()

    print('## Очередь сейчас')
    print()
    print(f'- Элементов в durable queue: **{len(queue)}**.')
    print(f'- Final-scored queue items: **{len(final_scores)}**.')
    print(f'- Pre-AI queue items: **{len(pre_ai_scores)}**.')
    if final_scores:
        print(f'- Final score range: **{min(final_scores):.1f}–{max(final_scores):.1f}**.')
    if pre_ai_scores:
        print(f'- Pre-AI score range: **{min(pre_ai_scores):.1f}–{max(pre_ai_scores):.1f}**.')
    print()
    print('| Диапазон | В очереди | Доля |')
    print('|---|---:|---:|')
    for name in ('0–39', '40–49', '50–59', '60–69', '70–79', '80–84', '85–89', '90–100'):
        print(f'| {name} | {buckets.get(name, 0)} | {pct(buckets.get(name, 0), len(scores))} |')
    print()

    print('## Последний запуск')
    print()
    print(f"- Кандидаты после отбора: **{latest.get('candidates', 0)}**.")
    print(f"- Добавлено в очередь: **{admission.get('added', 0)}**.")
    print(f"- Raw RSS/News materials: **{rss.get('raw_items', 0)}**.")
    print(f"- Published: **{latest.get('published', 0)}**.")
    print()

    print('## Распределение текущего durable queue')
    print()
    for name in ('0–39', '40–49', '50–59', '60–69', '70–79', '80–84', '85–89', '90–100'):
        print(f'- `{name}`: {buckets.get(name, 0)}')


if __name__ == '__main__':
    main()
