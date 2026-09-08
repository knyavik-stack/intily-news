# INTILY Project Status — 2026-09-08

## Canonical current status

**🟡 PRODUCTION VERIFICATION MODE / SCORING RUNTIME FIX DEPLOYED, LIVE CONFIRMATION PENDING**

The project has a 55-point final publication gate, a 70/30 deterministic+AI score architecture, finalized-queue hygiene, and a no-truncation photo-caption policy. A scoring runtime defect was found and fixed: the legacy runner was adding a phantom +10 audience bonus before AI evaluation, making a perfect base score appear as 80 instead of 70 and preventing the full 100-point contract from being observable. One real production cycle on the corrected runtime remains required before claiming GREEN.

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

## Base score model — restored and locked

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

These are point allocations, not arbitrary multipliers. The code fails fast if `sum(WEIGHTS) != BASE_MAX`, and component functions are bounded by their corresponding allocation.

## Root cause found 2026-09-08

The user's deliberate weight inflation exposed a second, deeper runtime defect. The deterministic model could reach its full 70-point base ceiling, but `scripts/intily_ai_news_runner.py` initialized `audience_bonus = 10.0` even when `audience_score` was still absent.

The observed state therefore became:

```text
base_score       = 70
 audience_score  = null
 audience_bonus  = 10
 final_score     = 80
```

This exactly explains the user's experiment. The missing 20 points were not disappearing inside the weights. The runtime was substituting a legacy +10 placeholder for the real AI contribution of up to +30. Therefore the maximum observable pre-AI score was artificially **80**, not the intended 70, and the full 100-point final contract was never observable without an AI result.

The intended arithmetic is:

```text
Deterministic base maximum     70
AI audience maximum             30
---------------------------------
Final maximum                  100
```

And by stage:

```text
pre-AI       = base + 0          → max 70
AI 1/10      = base + 3          → max 73
AI 5/10      = base + 15         → max 85
AI 10/10     = base + 30         → max 100
```

## Runtime fix

Added `scripts/intily_scoring_runtime_guard.py`.

The production workflow now runs through this guard. It intercepts the legacy runner's score assignment and enforces zero audience contribution before AI evaluation while preserving the real `audience_score × 3` contribution after evaluation.

Added `scripts/test_intily_scoring_runtime_guard.py` to lock the invariant.

The regression test is included in the production workflow before the news engine starts.

Full forensic record: `docs/SCORING_RUNTIME_BUG_2026-09-08.md`.

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

Run #687 (`34221093470`) then demonstrated candidate starvation: 843 materials were discovered, 15 scored candidates were admitted, all remained in the old ~45–49 base-score band, no AI provider call was made, and no story was published.

The scoring runtime fix and regression protection are now committed. Because the production workflow is configured for `workflow_dispatch`, the next scheduled/dispatch cycle is the authoritative live verification; no post-fix production result exists yet.

## Acceptance gate for GREEN

1. regression suite green;
2. base score ≤70;
3. pre-AI audience bonus = 0;
4. AI bonus +3…+30;
5. perfect base + AI 10/10 = 100;
6. every publication final ≥55;
7. `final_below_threshold=0`;
8. no finalized <55 in durable queue;
9. long photo post retains its full text;
10. image payload ≤1,000,000 bytes;
11. oversized candidate is skipped without transformation;
12. publisher image reaches `IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT` when source allows;
13. Telegram HTML formatting remains intact;
14. new score distribution shows strong stories moving above the historical 40–60 concentration;
15. provider failures do not create uncontrolled retry latency;
16. `sum(WEIGHTS) == BASE_MAX == 70` and every component is bounded by its declared allocation.

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
