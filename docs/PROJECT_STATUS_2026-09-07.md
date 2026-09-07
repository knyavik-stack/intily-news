# INTILY Project Status — 2026-09-07

## Canonical current status

**🟡 PRODUCTION OBSERVATION MODE / LIVE MEDIA VERIFICATION PENDING**

The production architecture, two-stage editorial model, audience-fit layer, Russian source expansion, publisher-first image resolver and strict 1 MB image policy are implemented. The latest production cycle exposed one regression in the new caption test; it has been fixed and must be re-verified by the next scheduled cycle.

## Current editorial policy

- Pre-AI gate: **40/100**.
- Final publication gate: **55/100**.
- Audience score: **1–10**.
- Audience bonus: **+2…+20**, exactly `audience_score × 2`.
- Final formula: `min(100, base_score + audience_score × 2)`.
- RU/WORLD portfolio target: approximately **40% / 60%**; geography is not a relevance bonus.

A 40–54 base candidate reaches AI editorial evaluation but is published only when final score is at least 55.

## Media policy

**1 MB is a hard reject, not a compression target.** If an image payload is larger than **1,000,000 bytes decimal**, it is skipped. No resize or recompression is performed to make it fit.

Production path:

```text
publisher article
  → image candidates
  → Google-host ban
  → publisher Referer fetch
  → >1,000,000 bytes? skip candidate
  → validate type + dimensions
  → safe caption ≤1024 chars after escaping
  → Telegram sendPhoto
```

If an oversized or broken candidate is encountered, the hardened resolver continues with the next publisher candidate. If no acceptable image remains, text-only fallback is allowed when editorial/publication gates pass.

## Verified production evidence

### Run #577 — root cause of the ~4-minute runtime

Run #577 (`34144899129`) started at **16:48:01 UTC** and completed at **16:51:58 UTC**, about **3m57s** wall-clock. The news search was explicitly skipped (`SEARCH_SKIPPED`), so RSS collection was not the cause.

The delay was AI provider retry/failover latency. Gemini encountered retry/503/timeout conditions; Groq returned HTTP 403 / error 1010 and was circuit-opened; OpenAI returned HTTP 429 / no credits and was circuit-opened. Multiple queued items were still attempted after provider degradation, including a second editorial attempt per item. The run ended `PUBLISH_FAILED` with 10 item failures.

### Run #578

Run #578 (`34145727924`) completed in about **28s**. A publisher-hosted image of **48,472 bytes** was found and validated, but the old `CAPTION_TOO_LONG` guard prevented `sendPhoto`. That guard has been replaced by a safe bounded caption path.

### Run #579

Run #579 (`34146591852`) started at **17:12:01 UTC** and failed fast during regression tests. The failure was real and useful: the first implementation bounded the raw caption before HTML escaping, so an input containing `&` expanded to **1028 characters** after escaping despite a 1024 raw-character cap.

The production code now bounds the **final escaped caption**, and the regression test has been corrected to assert that exact contract. The news engine was correctly skipped because CI failed; no publication was attempted from this invalid build.

## Latest code changes now on main

- Final publication threshold: **55**.
- Publisher and audience analytics use current threshold constants instead of historical hard-coded 60 values.
- Image hardening skips >1 MB candidates without compression and continues to the next candidate.
- Runtime keeps a second strict 1 MB defense-in-depth check.
- Photo captions are converted to safe plain text and bounded **after HTML escaping** to Telegram's 1024-character limit.
- Image regression coverage includes publisher resolution, candidate fallback, strict 1 MB rejection and safe caption bounds.
- Scoring policy was restored in full after the threshold edit; the scoring functions remain intact.

## Current acceptance gate

The next scheduled production cycle is the observation gate. It should verify:

1. all regression tests pass;
2. Publisher/Monitor visibly report final gate **55**;
3. 40–54 base stories can reach AI evaluation while final <55 is rejected;
4. no finalized queue item below 55 remains;
5. publisher image reaches `IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT`;
6. sent image payload is ≤1,000,000 bytes;
7. >1 MB candidates are skipped rather than transformed;
8. Google-hosted images remain forbidden;
9. no `CAPTION_TOO_LONG` fallback occurs for an otherwise valid image;
10. durable state/KPI persistence remains successful;
11. provider failures do not create uncontrolled runtime latency.

## Documentation hierarchy

This document is the canonical current status.

Related:

- `docs/INTILY_ANALYTICS.md`
- `docs/INTILY_PRODUCTION_MONITORING.md`
- `docs/INTILY_PUBLICATION_SETTINGS.md`
- `docs/RELEASE_2026-09-07.md`
- `docs/SCORING_CALIBRATION_2026-09-07.md`
- `docs/CMO_MODEL_REVIEW_2026-09-07.md`
- `docs/IMAGE_PIPELINE_INCIDENT_2026-09-07.md`
- `docs/PRODUCTION_CHANGELOG_2026-09-07_MEDIA_1MB.md`
- `docs/USER_HANDOFF.md`
- `docs/NEW_CHAT_START_PROMPT.md`
- `docs/INTILY_OPERATIONS.md`
