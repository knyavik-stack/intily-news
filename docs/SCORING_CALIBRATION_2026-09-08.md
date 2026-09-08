# INTILY — Scoring Calibration 2026-09-08

## Production contract

- Pre-AI gate: **40/100**.
- Base deterministic model: **0–70**.
- AI audience-fit: **1–10 → +3…+30**.
- AI contribution: exactly **30%** of the 100-point scale.
- Final score: `min(100, base_score + audience_score × 3)`.
- Final publication gate: **55/100**.

## Two separate scoring defects

### 1. Runtime placeholder defect

The legacy runner initialized `audience_bonus=10` before AI evaluation. Therefore a perfect deterministic base could appear as 80 instead of 70. The runtime guard now forces pre-AI audience bonus to zero and preserves the real AI contribution after editorial evaluation.

### 2. Deterministic calibration compression

The subsequent production observation showed **16 queue stories with a maximum base score around 52**. This was a different defect: the arithmetic weights summed to 70, but the component functions did not use their allocations effectively on real material.

The old formulas were structurally conservative:

- AI specificity often stopped at 2.5–4.1/6;
- impact commonly stayed in the lower half unless several signals aligned;
- event concreteness often stopped at 11–14/18;
- practical value commonly stopped at 2–5/8;
- evidence and freshness were bounded but frequently partial;
- novelty was explicitly 0.

So the system had a **nominal 70-point ceiling but a practical ceiling around 52 for the observed story mix**. The 18-point gap was a calibration problem, not a missing final-sum operation.

## Base model — 70 points

| Component | Max | v5 calibration principle |
|---|---:|---|
| AI relevance | 12 | Full allocation when the story is genuinely AI-relevant |
| AI specificity | 6 | 4 evidence tiers: 3 / 4.5 / 5.5 / 6 |
| Impact | 16 | consequence baseline + independent scale/actor/major/measurement/risk evidence |
| Event concreteness | 18 | event family + actor + major-event + measurement evidence |
| Practical value | 8 | 3 / 5 / 6.5 / 8 applicability tiers |
| Novelty | 0 | intentionally outside arithmetic until a defensible novelty model exists |
| Source quality | 5 | 5 trusted / 4 known / 2 other |
| Evidence | 3 | bounded evidence-density tiers, not length multiplication |
| Freshness | 2 | time-window based |
| **Total** | **70** | |

v5 is deliberately not a keyword-count multiplier. Multiple words from one sentence do not independently create unlimited points. The goal is to recognize independent evidence dimensions that were previously underweighted.

## AI audience-fit — 30 points

| Score | Contribution |
|---:|---:|
| 1 | +3 |
| 2 | +6 |
| 3 | +9 |
| 4 | +12 |
| 5 | +15 |
| 6 | +18 |
| 7 | +21 |
| 8 | +24 |
| 9 | +27 |
| 10 | +30 |

The AI asks what concrete consequence the news creates for a Russian-speaking AI-active professional. High scores require material effect on work, product, business, economics, technology strategy, regulation, security or risk.

Brand name, funding, valuation, rumor, forecast and dramatic framing do not justify 8–10/10 without a demonstrated consequence.

## Expected-value prior

The following is a **model calibration prior**, not observed subscriber behavior:

| Score | Probability | Contribution | Expected contribution |
|---:|---:|---:|---:|
| 1 | 1% | +3 | 0.03 |
| 2 | 2% | +6 | 0.12 |
| 3 | 4% | +9 | 0.36 |
| 4 | 7% | +12 | 0.84 |
| 5 | 12% | +15 | 1.80 |
| 6 | 18% | +18 | 3.24 |
| 7 | 24% | +21 | 5.04 |
| 8 | 16% | +24 | 3.84 |
| 9 | 11% | +27 | 2.97 |
| 10 | 5% | +30 | 1.50 |
| **Total / E[AI]** | **100%** | | **19.74/30** |

## Transparent publication diagnostics

Every published item now carries a compact score footer before media delivery:

```text
📊 Оценка новости
Итого: X/100 = база Y/70 + аудитория Z/30
AI-релевантность: …/12
AI-специфичность: …/6
Влияние: …/16
Конкретность события: …/18
Практическая ценность: …/8
Новизна: 0/0
Качество источника: …/5
Доказательность: …/3
Свежесть: …/2
Шум/низкий сигнал: …
Аудитория: …/10 → +…
```

This makes every point traceable and prevents future “where did the points go?” debugging from relying on aggregate telemetry alone.

## No-truncation rule

Editorial text is never sacrificed to satisfy Telegram's photo-caption limit. Telegram's `sendPhoto` caption is limited to 1024 characters after entity parsing. If the complete post plus diagnostics is too long for a photo caption, the image path must fall back to the complete text-only post. If the full text post itself exceeds the Telegram text limit, the publisher raises a controlled diagnostic-limit error rather than silently slicing content.

The image payload remains hard-capped at 1,000,000 bytes with no resize/recompression.

## GREEN acceptance gate

- CI regression suite green;
- base score ≤70;
- pre-AI audience bonus = 0;
- AI bonus +3…+30;
- perfect base + AI 10/10 = 100;
- strong real stories demonstrably use >55 base when evidence supports it;
- every published final score ≥55;
- `final_below_threshold=0`;
- no finalized <55 in durable queue;
- every publication contains the complete score footer;
- score footer never truncates editorial text;
- long photo captions never lose their tail;
- valid publisher image reaches `IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT` when source permits;
- strong stories move above the historical 40–60 concentration.
