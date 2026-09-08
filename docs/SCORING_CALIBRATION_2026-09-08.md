# INTILY — Scoring Calibration 2026-09-08

## Production contract

- Pre-AI gate: **40/100**.
- Base deterministic model: **0–70**.
- AI audience-fit: **1–10 → +3…+30**.
- AI contribution: exactly **30%** of the 100-point scale.
- Final score: `min(100, base_score + audience_score × 3)`.
- Final publication gate: **55/100**.

## Why the model was rebuilt

Production telemetry showed that materially important stories clustered around 40–60 base points. The former audience layer contributed at most +20, so it could not represent the agreed 30% AI editorial contribution.

Run #680 also exposed four finalized queue elements below 55. They were blocked by the final editor gate, but remained in durable queue. The queue invariant is now explicit: finalized <55 is rejected and removed; pre-AI 40–54 is valid until AI evaluation.

## Base model — 70 points

| Component | Max |
|---|---:|
| AI relevance | 12 |
| AI specificity | 6 |
| Impact | 16 |
| Event concreteness | 18 |
| Practical value | 8 |
| Source quality | 5 |
| Evidence | 3 |
| Freshness | 2 |
| **Total** | **70** |

The model is event/consequence-first. Keyword density is not the objective. Semantic uniqueness remains outside the arithmetic score.

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

This prior is intentionally conservative: it gives meaningful lift to useful stories while reserving +24…+30 for strong audience fit.

## Practical score interpretation

Examples of the new composition:

- base 35 + audience 6 = **53** → reject;
- base 40 + audience 6 = **58** → publishable;
- base 45 + audience 7 = **66** → solid A;
- base 55 + audience 8 = **79** → strong A+;
- base 65 + audience 9 = **92** → S.

This is the intended mechanism for moving genuinely important news out of the old 40–60 concentration without simply lowering the 55 gate.

## Media rule connected to scoring

Editorial text is never sacrificed to satisfy Telegram's photo-caption limit. If a sanitized photo caption exceeds 1024 characters, the full text is sent through text-only fallback. A photo is therefore optional; the integrity of the editorial post is not.

The image payload remains hard-capped at 1,000,000 bytes with no resize/recompression.

## GREEN acceptance gate

- CI regression suite green;
- base score ≤70;
- AI bonus +3…+30;
- every published final score ≥55;
- `final_below_threshold=0`;
- no finalized <55 in durable queue;
- long photo captions never lose their tail;
- valid publisher image reaches `IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT` when source permits;
- strong stories move above the historical 40–60 concentration.
