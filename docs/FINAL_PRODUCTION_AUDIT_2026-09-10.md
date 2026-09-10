# INTILY — Final Production Audit — 2026-09-10

## Executive status

**Overall readiness: 80% — YELLOW / production verification mode.**

Core publication is production-capable and has been proven end-to-end. The latest CI regression was a defect in the new media tests, not in the publisher; it is fixed. A runtime inspection also exposed a legacy editor-prompt defect and corrected it through the production compatibility layer. Fresh production evidence is still required after these corrections.

## Product contract

Telegram posts contain **editorial content only**. Queue statistics, queue-next information and operational diagnostics are disabled in posts.

`SHOW_QUEUE_DIAGNOSTICS = False`

Current runtime policy also enforces a 3-minute minimum publication interval and an 80% target joke probability where context permits. Serious safety/law/accident/harm/incident topics suppress humor.

## Latest CI incident — run #951

Run #951 failed at the regression gate before publisher execution.

Root cause: both image-hardening tests mocked `extract_image_candidates()` as a list, while the real function returns `(ranked_candidates, final_url)`. This produced:

`ValueError: not enough values to unpack (expected 2, got 1)`

Fix: `5415478c418263ab3e8233ff731584a90b5ee198`.

The regression gate correctly prevented an unverified publisher run.

## Latest runtime correction

Inspection of the legacy `build_edit_prompt()` found an unsuitable historical prompt that required excessive profanity and an inappropriate character style. That was inconsistent with the intended INTILY editorial contract.

`scripts/sitecustomize.py` now overrides the legacy prompt at production runtime and also pins:

- Groq model: `openai/gpt-oss-20b`;
- publication minimum interval: 3 minutes;
- joke target probability: 80%.

Commit: `1060cf2971855a4bd4daa7ec7d3aa4e39443b89e`.

This correction is source-verified but not yet production-proven on a fresh publisher run.

## Live production evidence — run #949

Run #949 proved:

- 47 regression tests passed at that revision;
- `GROQ_MODEL_RUNTIME_OVERRIDE openai/gpt-oss-20b` loaded;
- Gemini edited candidates;
- Telegram text publication succeeded: `TELEGRAM_SENT 1134`;
- `BUSINESS_RESULT PUBLISHED telegram_delivery_ok`;
- `QUEUE_SCORE_AUDIT invariant_ok:true`;
- state and analytics persisted.

It did not prove Groq fallback and did not prove photo delivery.

## Groq gate

The retired `llama-3.1-8b-instant` produced the historical `404 svgmodel_not_found`. The runtime now selects `openai/gpt-oss-20b`.

Closure requires a real fallback telemetry sequence:

`AI_PROVIDER_ATTEMPT GROQ` → `AI_PROVIDER_OK GROQ`

or a bounded correctly classified Groq failure.

## Photo gate

The previous live publisher run ended in text fallback (`found=0`, `validated=0`, `photo_sent=0`).

Current media hardening provides:

- browser-like retries;
- one-level HTML image indirection;
- nested candidate deduplication;
- 12s total image-fetch budget;
- 6s individual request timeout;
- Google-hosted image prohibition;
- MIME/dimension checks;
- Telegram ≤1 MB payload cap.

Closure requires:

`IMAGE_FOUND` → `IMAGE_VALIDATED` → `TELEGRAM_PHOTO_SENT`

If this fails again, implement first-class RSS/Atom media extraction (`media:content`, `media:thumbnail`, `enclosure`) and pass the hints into the image runtime. Do not use random Google Images.

## Scheduler / cadence

GitHub Actions is `workflow_dispatch` only. Cloudflare is the production scheduler.

The current versioned worker uses `* * * * *` UTC with a 1/3 dispatch gate. This is probabilistic dispatch, not a guaranteed 3- or 5-minute cadence. Several real runs are required to measure actual cadence.

The Python publisher has a separate 3-minute minimum publication interval.

## Current runtime

- lookback: 12h;
- healthy-queue search interval: 30m;
- urgent search: queue ≤1;
- max publish per cycle: 1;
- importance threshold: 60;
- queue cap: 20;
- RU target share: 60% when enough qualifying RU supply exists;
- joke target probability: 80% where context permits;
- Telegram queue diagnostics: disabled.

## Remaining gates

1. Fresh regression run after the latest fixes.
2. Real Groq fallback proof.
3. Real Telegram photo proof.
4. Several consecutive successful Cloudflare-dispatched cycles.
5. Confirm acceptable cadence under normal queue conditions.

## Final assessment

**80% — YELLOW. Production-capable, not yet fully GREEN.**

Acceptance rule:

**fact → root cause → implementation → tests → real production run → telemetry inspection → documentation.**
