# INTILY Project Status — 2026-09-08

## Canonical current status

**🟡 PRODUCTION VERIFICATION MODE / MODEL + MEDIA FIXES DEPLOYED, LIVE CONFIRMATION PENDING**

The project now has a 55-point final publication gate, a 70/30 deterministic+AI score architecture, finalized-queue hygiene, and a no-truncation photo-caption policy. One real production cycle on the new code remains required before claiming GREEN.

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

## Base score model

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

The model is event/consequence-first rather than keyword-density-first. Semantic uniqueness remains outside the arithmetic score.

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

The latest commits after #680 change the score model, queue guard, media behavior, tests and documentation. No GitHub status checks exist yet for the new HEAD because the production workflow is configured for `workflow_dispatch`; the next scheduled/dispatch cycle is the authoritative verification.

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
13. provider failures do not create uncontrolled retry latency.

## Canonical related docs

- `docs/INTILY_ANALYTICS.md`
- `docs/INTILY_PRODUCTION_MONITORING.md`
- `docs/INTILY_PUBLICATION_SETTINGS.md`
- `docs/SCORING_CALIBRATION_2026-09-07.md`
- `docs/CMO_MODEL_REVIEW_2026-09-07.md`
- `docs/IMAGE_PIPELINE_INCIDENT_2026-09-07.md`
- `docs/USER_HANDOFF.md`
- `docs/NEW_CHAT_START_PROMPT.md`
- `docs/INTILY_OPERATIONS.md`
