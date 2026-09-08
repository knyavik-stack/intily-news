# INTILY Project Status — 2026-09-08

## Canonical current status

**🟡 PRODUCTION VERIFICATION MODE / MODEL + MEDIA FIXES DEPLOYED, LIVE CONFIRMATION PENDING**

The project has a corrected 55-point final publication gate, a 70/30 deterministic+AI score architecture, queue hygiene for finalized rejects, and a no-truncation photo-caption policy. The remaining acceptance step is one real production cycle on the new code to verify the new score distribution and publisher image delivery.

## Current editorial policy

- Pre-AI gate: **40/100**.
- Final publication gate: **55/100**.
- Base deterministic model: **0–70**.
- AI audience-fit: **1–10 → +3…+30**.
- AI layer: exactly **30% of the 100-point scale**.
- Final formula: `min(100, base_score + audience_score × 3)`.
- Finalized `score_stage=final` items below 55 are not allowed to remain in durable queue.
- RU/WORLD portfolio target: approximately **40% / 60%**; geography is not an editorial score bonus.

### Base model

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

## Audience model

The AI editor now evaluates concrete consequence for the target Russian-speaking AI-active professional. The rubric was tightened so that funding, valuation, brand name, rumors and generic commentary do not receive high audience scores without a demonstrated consequence.

Audience contribution:

`1→+3, 2→+6, 3→+9, 4→+12, 5→+15, 6→+18, 7→+21, 8→+24, 9→+27, 10→+30`.

Working probability prior is documented in `docs/SCORING_CALIBRATION_2026-09-07.md`; it is explicitly a model calibration hypothesis, not subscriber statistics. Expected AI contribution under that prior is **19.74/30**.

## Queue defect found and closed

Run #680 (`34219243075`) showed:

- one publication at final score **69.1**;
- audience score 7/10 under the old ×2 layer;
- `final_below_threshold=4` in durable queue.

Those four items were not evidence of publication below 55 because the AI editor gate blocked final scores below 55. They were nevertheless a real queue invariant violation: finalized rejects should not remain durable candidates. A guard now removes `score_stage=final` items below 55 during queue rebalancing. Pre-AI 40–54 remains valid until AI evaluation.

## Media policy

**1 MB remains a hard reject.** No resize or recompression is used to make an image fit.

The production media path is:

```text
publisher article
  → image candidates
  → Google-host ban
  → publisher Referer fetch
  → >1,000,000 bytes? skip candidate
  → validate type + dimensions
  → preserve/sanitize Telegram HTML
  → caption ≤1024?
       yes → sendPhoto
       no  → complete text-only fallback
```

The important change is that **photo captions are no longer truncated**. Telegram's 1024-character caption limit is treated as a delivery constraint, not a reason to delete the tail of the editorial post. If the complete sanitized caption is too long, the full text is sent without the image.

## Production evidence

### Run #680

CI: green, 21 regression tests passed. Production published one item at final score 69.1. Image path fell back on HTTP 403. This run used the previous ×2 audience layer and therefore is not a validation run for the new 70/30 model.

### Historical image incident

The previous photo formatting regression was caused by stripping all Telegram HTML before `sendPhoto`. That code path has been replaced by formatting-preserving sanitization. The new no-truncation policy also removes the second class of defect: a valid post cannot lose its final section merely because an image is attached.

## Current acceptance gate

The next real production cycle is the final verification gate:

1. all regression tests pass;
2. `BASE_MAX=70` and no base score exceeds 70;
3. AI bonus is exactly +3…+30;
4. every publication has final score ≥55;
5. `final_below_threshold=0`;
6. no final <55 item remains in durable queue;
7. a long photo post never loses its tail;
8. image payload ≤1,000,000 bytes;
9. oversized first image candidate is skipped and next candidate is tried;
10. publisher image reaches `IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT` when source permits;
11. Telegram HTML formatting remains intact;
12. provider failure does not create uncontrolled retry latency;
13. new score distribution moves strong stories out of the historical 40–60 concentration.

## Documentation hierarchy

This document is canonical current status.

Related:

- `docs/INTILY_ANALYTICS.md`
- `docs/INTILY_PRODUCTION_MONITORING.md`
- `docs/INTILY_PUBLICATION_SETTINGS.md`
- `docs/SCORING_CALIBRATION_2026-09-07.md`
- `docs/CMO_MODEL_REVIEW_2026-09-07.md`
- `docs/IMAGE_PIPELINE_INCIDENT_2026-09-07.md`
- `docs/PRODUCTION_CHANGELOG_2026-09-07_MEDIA_1MB.md`
- `docs/USER_HANDOFF.md`
- `docs/NEW_CHAT_START_PROMPT.md`
- `docs/INTILY_OPERATIONS.md`
