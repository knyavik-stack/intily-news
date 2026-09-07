#!/usr/bin/env python3
"""CMO/editorial analytics for Intily Production Monitor.

Reads durable run_history only. It never calls Telegram, RSS or an AI provider.
"""
import json
import time
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parents[1] / 'data' / 'intily-ai-news-state.json'


def load():
    with STATE_PATH.open('r', encoding='utf-8') as f:
        return json.load(f)


def window(rows, seconds, now):
    return [r for r in rows if now - float(r.get('ts', 0) or 0) <= seconds]


def aggregate(rows):
    blocks = [r.get('admission', {}).get('audience', {}) for r in rows]
    evaluated = sum(int(x.get('evaluated', 0) or 0) for x in blocks)
    bonus = sum(float(x.get('bonus_total', 0) or 0) for x in blocks)
    weighted_score_sum = sum(
        float(x.get('average_score', 0) or 0) * int(x.get('evaluated', 0) or 0)
        for x in blocks
    )
    high_fit = sum(int(x.get('high_fit_8_10', 0) or 0) for x in blocks)
    avg = weighted_score_sum / evaluated if evaluated else None
    pubs = sum(int(r.get('published', 0) or 0) for r in rows)
    queue_audits = [r.get('admission', {}).get('queue_score_audit', {}) for r in rows]
    pre_ai_below = sum(int(x.get('pre_ai_below_final_threshold', 0) or 0) for x in queue_audits)
    final_below = sum(int(x.get('final_below_threshold', 0) or 0) for x in queue_audits)
    return {
        'evaluated': evaluated,
        'bonus': bonus,
        'average_score': avg,
        'average_bonus': bonus / evaluated if evaluated else None,
        'high_fit': high_fit,
        'high_fit_rate': high_fit / max(1, evaluated) * 100,
        'published': pubs,
        'pre_ai_below': pre_ai_below,
        'final_below': final_below,
    }


def portfolio(state):
    regions = list(state.get('publication_regions', []) or [])[-20:]
    ru = regions.count('RUSSIA')
    world = regions.count('WORLD')
    return ru, world, ru / len(regions) * 100 if regions else None


def main():
    state = load()
    rows = state.get('run_history', [])
    now = time.time()
    d24 = aggregate(window(rows, 86400, now))
    d7 = aggregate(window(rows, 7 * 86400, now))
    stored = aggregate(rows)
    ru, world, ru_share = portfolio(state)

    print('## CMO / Target Audience / Editorial Fit')
    print('')
    print('Модель: AI-активные русскоязычные предприниматели, руководители, product/marketing/sales/operations/HR/finance специалисты, разработчики и AI power users.')
    print('AI оценивает полезность новости одновременно с переводом/пересказом: 1–10 → линейный bonus +2…+20.')
    print('Pre-AI gate = 40; final publication gate = 60.')
    print('')
    print('| Показатель | 24 часа | 7 дней | История |')
    print('|---|---:|---:|---:|')
    print(f"| AI-оценок аудитории | {d24['evaluated']} | {d7['evaluated']} | {stored['evaluated']} |")
    print(f"| Средняя оценка | {d24['average_score']:.2f} | {d7['average_score']:.2f} | {stored['average_score']:.2f} |" if d24['average_score'] is not None else '| Средняя оценка | — | — | — |')
    print(f"| Средний bonus | +{d24['average_bonus']:.2f} | +{d7['average_bonus']:.2f} | +{stored['average_bonus']:.2f} |" if d24['average_bonus'] is not None else '| Средний bonus | — | — | — |')
    print(f"| Суммарный audience bonus | +{d24['bonus']:.1f} | +{d7['bonus']:.1f} | +{stored['bonus']:.1f} |")
    print(f"| Оценки 8–10 | {d24['high_fit']} ({d24['high_fit_rate']:.1f}%) | {d7['high_fit']} ({d7['high_fit_rate']:.1f}%) | {stored['high_fit']} ({stored['high_fit_rate']:.1f}%) |")
    print(f"| Pre-AI < 60 | {d24['pre_ai_below']} | {d7['pre_ai_below']} | {stored['pre_ai_below']} |")
    print(f"| Final < 60 (инвариант) | {d24['final_below']} | {d7['final_below']} | {stored['final_below']} |")
    print('')
    print('## Географический портфель')
    print('')
    print(f'Последние {ru + world if ru + world else 0} публикаций: RU={ru}, WORLD={world}, RU share={ru_share:.1f}%.' if ru_share is not None else 'Публикаций для расчёта пока нет.')
    print('Целевой портфель: около 40% RU / 60% WORLD; география не меняет математическую релевантность новости.')
    print('')
    print('### Как читать')
    print('')
    print('- **8–10/10** — сильная полезность для целевой аудитории, bonus +16…+20.')
    print('- **6–7/10** — полезный профессиональный контекст, bonus +12…+14.')
    print('- **1–5/10** — bonus +2…+10; низкая оценка не обнуляет редакционную ценность, но почти не помогает пройти финальный gate.')
    print('- **Final < 60 = 0** — обязательный инвариант. Pre-AI < 60 допустим, потому что AI-аудит ещё не проведён.')


if __name__ == '__main__':
    main()
