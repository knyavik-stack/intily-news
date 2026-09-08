# INTILY Project Status — 2026-09-08

## Canonical current status

**🟡 PRODUCTION VERIFICATION MODE / SCORING RUNTIME + CALIBRATION REBUILD DEPLOYED, LIVE CONFIRMATION PENDING**

The project has a 55-point final publication gate, a 70/30 deterministic+AI score architecture, finalized-queue hygiene, and a no-truncation photo-caption policy. Two distinct scoring defects have now been identified: a legacy pre-AI +10 audience placeholder and, separately, an under-utilized deterministic scoring curve that caused real stories to cluster around 40–52 despite a nominal 70-point ceiling. Both are addressed in code; live confirmation of the rebuilt curve remains pending.

## Editorial contract

- Pre-AI gate: **40/100**.
- Base deterministic model: **0–70**.
- AI audience-fit: **1–10 → +3…+30**.
- AI contribution: exactly **30% of the 100-point scale**.
- Final formula after AI: `min(100, base_score + audience_score × 3)`.
- Final publication gate: **55/100**.
- Pre-AI score contains **no audience bonus**.
- `score_stage=final` with score <55 is forbidden in durable queue.
- `score_stage=pre_ai` with base 40–54 is valid until AI evaluation.
- RU/WORLD target: ~40/60; geography is not a relevance bonus.

## Base score model — v5 recalibrated

| Component | Max |
|---|---:|
| AI relevance | 12 |
| AI specificity | 6 |
| Impact | 16 |
| Event concreteness | 18 |
| Practical value | 8 |
| Novelty | 0 |
| Source quality | 5 |
| Evidence | 3 |
| Freshness | 2 |
| **Total** | **70** |

The previous model had correct nominal allocations but conservative internal sub-formulas. Production evidence showed a hard practical ceiling around **52** for the active story mix: many components were receiving only their low evidence tier even when the material described a real launch, acquisition, research result, regulation or implementation event. This was a calibration defect, not missing arithmetic.

v5 changes the internal curves to evidence tiers rather than keyword-count multiplication. Strong stories can now legitimately use the upper half of the 70-point base range, while generic commentary remains below the final gate.

The code still fails fast if `sum(WEIGHTS) != BASE_MAX`, and every component remains bounded by its allocation.

## Root cause #1 — runtime audience placeholder

The user's deliberate weight inflation exposed a runtime defect. `scripts/intily_ai_news_runner.py` initialized `audience_bonus = 10.0` even when `audience_score` was still absent.

Observed state:

```text
base_score       = 70
 audience_score  = null
 audience_bonus  = 10
 final_score     = 80
```

The intended arithmetic is:

```text
Deterministic base maximum     70
AI audience maximum             30
---------------------------------
Final maximum                  100
```

By stage:

```text
pre-AI       = base + 0          → max 70
AI 1/10      = base + 3          → max 73
AI 5/10      = base + 15         → max 85
AI 10/10     = base + 30         → max 100
```

## Root cause #2 — nominal 70-point model, practical ~52-point ceiling

The next production observation showed **16 queued stories with the highest base score around 52**. This was not the previous +10 runtime issue: the 52-point ceiling was visible before AI audience scoring.

Forensic review of `scripts/intily_scoring_policy.py` showed that the nominal weights summed to 70, but the old component formulas commonly produced:

- AI specificity around 2.5–4.1 of 6;
- impact around 4–10.5 of 16 unless multiple independent signals aligned;
- event concreteness often 11–14 of 18;
- practical value around 2–5 of 8;
- evidence/freshness usually below their maxima;
- novelty explicitly fixed at 0.

The result was a structurally compressed distribution. The code had a 70-point ceiling but the evidence-to-points mapping rarely reached it. The user's 52-point observation was therefore correct.

### Correction — scoring policy v5

The scoring curve was rebuilt around independent evidence tiers:

- specificity: 3 / 4.5 / 5.5 / 6;
- impact: consequence baseline + independent scale/actor/major-signal/measurement/risk tiers;
- event concreteness: event-family baseline + actor + major-event + measurement evidence;
- practical value: 3 / 5 / 6.5 / 8 tiers by independent applicability evidence;
- event vocabulary expanded for announcement/release/update/regulation and Russian equivalents;
- source quality remains capped at 5;
- evidence remains bounded at 3;
- freshness remains bounded at 2;
- low-signal penalty remains explicit and subtractive;
- no geography bonus is included in mathematical relevance.

This is intentionally a **calibration rebuild**, not a lowering of the 55 publication gate.

## Transparent score shown inside every post

Every publication now receives a compact footer before image delivery:

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

The footer is diagnostic telemetry for the channel owner, not a hidden score. It is added without truncation. Telegram `sendPhoto` captions are limited to 1024 characters; if the complete post plus score footer is too long for a photo caption, the existing image pipeline must fall back to the complete text-only post rather than cutting the tail. Telegram text messages remain bounded separately by 4096 characters.

Regression tests now explicitly verify every component appears and that over-limit content raises a controlled error instead of being sliced.

## Runtime fix

Added `scripts/intily_scoring_runtime_guard.py`.

The production workflow runs through this guard. It intercepts the legacy runner's score assignment and enforces zero audience contribution before AI evaluation while preserving the real `audience_score × 3` contribution after evaluation.

The same guard now attaches the per-post score breakdown after editorial generation and before image delivery.

## Audience model

The AI editor evaluates concrete consequence for the Russian-speaking AI-active professional. High scores require material impact on work, product, business, economics, technology strategy, regulation, security or risk. Brand name, funding, valuation, rumor or forecast alone do not justify 8–10/10.

AI contribution is linear:

`1→+3, 2→+6, 3→+9, 4→+12, 5→+15, 6→+18, 7→+21, 8→+24, 9→+27, 10→+30`.

The documented calibration prior has expected AI contribution **19.74/30**. This is a model prior, not subscriber statistics.

## Bugs closed from production evidence

### Final-score/queue defect

Run #680 (`34219243075`) published one story at final 69.1 under the old ×2 layer but reported `final_below_threshold=4`. Those items were not published below 55; the editor gate rejected them. They nevertheless violated the durable queue invariant. A queue guard now removes finalized items below 55 during rebalancing.

### Photo post truncation

Telegram photo captions are limited to 1024 characters. The previous implementation truncated long captions, causing the user-visible tail of photo posts to disappear. The new policy never truncates editorial text. If the complete sanitized caption is >1024, the photo path falls back to the full text-only post.

Supported Telegram HTML formatting remains preserved and unsafe markup/links are sanitized.

### Image size

1,000,000 bytes is a hard cap. No resize or recompression is performed. Oversized/broken first candidates are skipped and the next publisher candidate is attempted.

## Last verified production evidence

Run #680 passed 21 regression tests and published one story. It also hit HTTP 403 on the image path, so the new publisher-image path still needs live confirmation.

Run #687 (`34221093470`) demonstrated candidate starvation: 843 materials were discovered, 15 scored candidates were admitted, all remained in the old ~45–49 base-score band, no AI provider call was made, and no story was published.

Run #743 (`34258981071`) executed 28 tests but failed only because the newly added runtime-guard regression fixture at that commit did not actually assign the score through the proxy. The production publisher was skipped; this was a test-fixture defect, subsequently corrected.

A post-v5 live production run has not yet been verified. The current state must therefore remain YELLOW until the rebuilt scoring curve is exercised against real discovery data and at least one real publication.

## Acceptance gate for GREEN

1. regression suite green;
2. base score ≤70;
3. pre-AI audience bonus = 0;
4. AI bonus +3…+30;
5. perfect base + AI 10/10 = 100;
6. strong real stories demonstrably use >55 base when evidence supports it;
7. every publication final ≥55;
8. `final_below_threshold=0`;
9. no finalized <55 in durable queue;
10. every publication contains the complete score breakdown;
11. score footer does not truncate editorial text;
12. long photo post retains its full text via text fallback;
13. image payload ≤1,000,000 bytes;
14. oversized candidate is skipped without transformation;
15. publisher image reaches `IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT` when source allows;
16. Telegram HTML formatting remains intact;
17. new score distribution shows strong stories moving above the historical 40–60 concentration;
18. provider failures do not create uncontrolled retry latency;
19. `sum(WEIGHTS) == BASE_MAX == 70` and every component is bounded by its declared allocation.

## Canonical related docs

- `docs/SCORING_RUNTIME_BUG_2026-09-08.md`
- `docs/INTILY_ANALYTICS.md`
- `docs/INTILY_PRODUCTION_MONITORING.md`
- `docs/INTILY_PUBLICATION_SETTINGS.md`
- `docs/SCORING_CALIBRATION_2026-09-08.md`
- `docs/CMO_MODEL_REVIEW_2026-09-07.md`
- `docs/IMAGE_PIPELINE_INCIDENT_2026-09-07.md`
- `docs/USER_HANDOFF.md`
- `docs/NEW_CHAT_START_PROMPT.md`
- `docs/INTILY_OPERATIONS.md`
