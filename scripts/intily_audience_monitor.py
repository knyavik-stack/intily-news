#!/usr/bin/env python3
"""Target-audience analytics for Intily Production Monitor.

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
    scores = []
    high_fit = 0
    for x in blocks:
        last = x.get('last') or {}
        if x.get('evaluated') and last.get('score') is not None:
            # Durable KPI stores the last score per cycle. Repeated cycles can
            # have multiple evaluations, so this is deliberately conservative.
            scores.append(float(last['score']))
        high_fit += int(x.get('high_fit_8_10', 0) or 0)
    avg = sum(scores) / len(scores) if scores else None
    pubs = sum(int(r.get('published', 0) or 0) for r in rows)
    return {
        'evaluated': evaluated,
        'bonus': bonus,
        'avg_last_cycle_score': avg,
        'high_fit': high_fit,
        'high_fit_rate': high_fit / max(1, evaluated) * 100,
        'published': pubs,
    }


def main():
    state = load()
    rows = state.get('run_history', [])
    now = time.time()
    d24 = aggregate(window(rows, 86400, now))
    d7 = aggregate(window(rows, 7 * 86400, now))
    stored = aggregate(rows)

    print('## Целевая аудитория: AI-fit')
    print('')
    print('Модель: практические AI-профессионалы — владельцы/фаундеры, руководители и менеджеры, product/marketing/operations, разработчики и другие AI decision-makers.')
    print('AI оценивает полезность новости для этой аудитории одновременно с переводом/пересказом; оценка 1–10 даёт дополнительный bonus только выше 5/10.')
    print('')
    print('| Показатель | 24 часа | 7 дней | История |')
    print('|---|---:|---:|---:|')
    print(f"| AI-оценок аудитории | {d24['evaluated']} | {d7['evaluated']} | {stored['evaluated']} |")
    print(f"| Средняя последняя оценка цикла | {d24['avg_last_cycle_score']:.2f} | {d7['avg_last_cycle_score']:.2f} | {stored['avg_last_cycle_score']:.2f} |" if d24['avg_last_cycle_score'] is not None else '| Средняя последняя оценка цикла | — | — | — |')
    print(f"| Суммарный audience bonus | +{d24['bonus']:.1f} | +{d7['bonus']:.1f} | +{stored['bonus']:.1f} |")
    print(f"| Оценки 8–10 | {d24['high_fit']} ({d24['high_fit_rate']:.1f}%) | {d7['high_fit']} ({d7['high_fit_rate']:.1f}%) | {stored['high_fit']} ({stored['high_fit_rate']:.1f}%) |")
    print('')
    print('### Как читать')
    print('')
    print('- **8–10/10** — материал явно полезен целевой аудитории и должен получать сильный audience bonus.')
    print('- **6–7/10** — полезный профессиональный контекст, но без сильного срочного эффекта.')
    print('- **1–5/10** — audience bonus не добавляется; новость не должна проходить только за счёт популярности темы.')
    print('- Финальный score = базовая редакционная оценка + audience bonus, с общим порогом публикации 60.')


if __name__ == '__main__':
    main()
