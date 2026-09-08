# INTILY Project Status — 2026-09-08

## Canonical current status

**🟡 PRODUCTION VERIFICATION MODE / SCORING WEIGHT CONTRACT RESTORED, LIVE CONFIRMATION PENDING**

The project has a 55-point final publication gate, a 70/30 deterministic+AI score architecture, finalized-queue hygiene, and a no-truncation photo-caption policy. The scoring layer had a concrete regression: the point allocations in `scripts/intily_scoring_policy.py` had been changed so their declared weights no longer represented the 70-point base budget, and the freshness component could exceed its own allocation. The weight contract is now restored and enforced in code/tests. One real production cycle on the new code remains required before claiming GREEN.

## Editorial contract

- Pre-AI gate: **40/100**.
- Base deterministic model: **0–70**.
- AI audience-fit: **1–10 → +3…+30**.
- AI contribution: exactly **30% of the 100-point scale**.
- Final formula: `min(100, base_score + audience_score × 3)`.
- Final publication gate: **55/100**.
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

These are **point allocations**, not arbitrary multipliers. The code now fails fast if `sum(WEIGHTS) != BASE_MAX`, and component functions are bounded by their corresponding allocation. This prevents a silent 70-point model from becoming a different scale through weight edits.

The model is event/consequence-first rather than keyword-density-first. Semantic uniqueness remains outside the arithmetic score.

## Root cause found 2026-09-08

The production scoring file had drifted from the canonical 70-point calibration. Its declared allocations had become `17+11+21+23+13+0+10+6+4 = 105`, while the public contract still said 70. The final clamp hid the inconsistency instead of exposing it. In addition, freshness returned up to 7 points while its documented allocation was only 2 points. This made the arithmetic contract internally inconsistent and made score behavior difficult to reason about.

The fix restores the canonical allocations, restores `AI_MAX=30`, caps freshness at its 2-point allocation, and adds a hard invariant plus regression tests for the exact budget. This is the scoring defect identified during the user's manual weight perturbation test.

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

Run #687 (`34221093470`) then demonstrated candidate starvation: 843 materials were discovered, 15 scored candidates were admitted, all remained in the old ~45–49 base-score band, no AI provider call was made, and no story was published. This is why the score contract must be fixed before further tuning of thresholds or deduplication.

The scoring-weight fix is committed in the current main branch, followed by explicit regression tests. Because the production workflow is configured for `workflow_dispatch`, the next scheduled/dispatch cycle is the authoritative live verification; no post-fix production result exists yet.

## Acceptance gate for GREEN

1. regression suite green;
2. base score ≤70;
3. AI bonus +3…+30;
4. every publication final ≥55;
5. `final_below_threshold=0`;
6. no finalized <55 in durable queue;
7. long photo post retains its full text;
8. image payload ≤1,000,000 bytes;
9. oversized candidate is skipped without transformation;
10. publisher image reaches `IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT` when source allows;
11. Telegram HTML formatting remains intact;
12. new score distribution shows strong stories moving above the historical 40–60 concentration;
13. provider failures do not create uncontrolled retry latency;
14. `sum(WEIGHTS) == BASE_MAX == 70` and every component is bounded by its declared allocation.

## Canonical related docs

- `docs/INTILY_ANALYTICS.md`
- `docs/INTILY_PRODUCTION_MONITORING.md`
- `docs/INTILY_PUBLICATION_SETTINGS.md`
- `docs/SCORING_CALIBRATION_2026-09-08.md`
- `docs/CMO_MODEL_REVIEW_2026-09-07.md`
- `docs/IMAGE_PIPELINE_INCIDENT_2026-09-07.md`
- `docs/USER_HANDOFF.md`
- `docs/NEW_CHAT_START_PROMPT.md`
- `docs/INTILY_OPERATIONS.md`
