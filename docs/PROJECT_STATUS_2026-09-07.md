# INTILY Project Status — 2026-09-07

## Canonical current status

**🟡 PRODUCTION OBSERVATION MODE / LIVE MEDIA VERIFICATION PENDING**

The production architecture, two-stage editorial model, audience-fit layer, Russian source expansion, publisher-first image resolver and strict 1 MB image policy are implemented. The latest cycle is technically green. The remaining verification target is a fresh qualifying Telegram photo on the newest media/caption code, plus observation of the new 55-point publication gate.

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
  → safe caption ≤1024 chars
  → Telegram sendPhoto
```

If an oversized or broken candidate is encountered, the hardened resolver continues with the next publisher candidate. If no acceptable image remains, text-only fallback is allowed when editorial/publication gates pass.

## Verified production evidence

### Run #577 — root cause of the ~4-minute runtime

Run #577 (`34144899129`) started at **16:48:01 UTC** and completed at **16:51:58 UTC**, about **3m57s** wall-clock. The news search was explicitly skipped (`SEARCH_SKIPPED`), so RSS collection was not the cause.

The delay was AI provider retry/failover latency:

- Gemini encountered retry/503/timeout conditions;
- Groq returned HTTP 403 / error 1010 and was circuit-opened;
- OpenAI returned HTTP 429 / no credits and was circuit-opened;
- multiple queued items were still attempted after provider degradation, including a second editorial attempt per item.

The run ended `PUBLISH_FAILED` with 10 item failures. This is a provider availability/retry-budget problem, not a slow news collector.

### Run #578

Run #578 (`34145727924`) started at **17:00:01 UTC** and completed at **17:00:29 UTC**, about **28s**. It used the latest status commit at that time and completed all workflow steps successfully.

It demonstrated a real publisher-hosted image path: the image payload was **48,472 bytes**, but the photo was not sent because the old caption guard emitted `CAPTION_TOO_LONG`. That guard has now been replaced with a safe bounded caption builder. Therefore Run #578 proves image discovery/validation but **does not yet prove Telegram photo delivery**.

## Latest code changes now on main

- Final publication threshold changed to **55**.
- Audience monitor and policy analytics now import live threshold constants instead of hard-coded historical 60 values.
- Image hardening skips >1 MB candidates without compression and continues to the next candidate.
- Photo captions are converted to safe plain text and bounded to Telegram's 1024-character caption limit.
- Runtime remains defense-in-depth: it rejects any payload >1,000,000 bytes.
- Image regression tests cover strict 1 MB rejection and safe captions.
- Scoring policy was restored in full after threshold update; no scoring functions were intentionally removed.

## Current acceptance gate

The system is now in **observation mode**. The next qualifying production cycle should verify:

1. CI/18 regression tests remain green;
2. final gate is visibly **55** in Publisher/Monitor analytics;
3. a 40–54 base story can reach AI evaluation and only final 55+ is publishable;
4. no final queue item below 55 remains;
5. publisher image reaches `IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT`;
6. sent image payload is ≤1,000,000 bytes;
7. >1 MB candidates are skipped rather than transformed;
8. Google-hosted images remain forbidden;
9. safe caption path no longer causes `CAPTION_TOO_LONG`;
10. durable state/KPI persistence remains successful;
11. provider failures do not create uncontrolled runtime latency.

## Analytics contract

**Publisher Summary** = current cycle only.

**Production Monitor** = 24h / 7d / stored history.

Both now use the current editorial threshold and current media policy. Historical documents may retain old values as historical records, but canonical current docs must not present them as live settings.

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
