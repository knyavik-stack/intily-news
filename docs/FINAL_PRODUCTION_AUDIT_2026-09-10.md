# INTILY — Final Production Audit — 2026-09-10

## Executive status

**Overall readiness: 80% — YELLOW / production verification mode.**

Core publication is proven end-to-end. CI regression was fixed. The contaminated legacy editor prompt was corrected and the correction was proven in production run #953. The media investigation advanced materially: #953 obtained a real 41 KB image payload, but photo delivery was blocked by the Telegram caption-length guard. A fresh run after the latest 350-character prompt correction is still required.

## Product contract

Telegram posts contain **editorial content only**. Queue statistics, queue-next information and operational diagnostics are disabled in posts.

`SHOW_QUEUE_DIAGNOSTICS = False`

Current runtime policy:

- 3-minute minimum publication interval;
- 80% target joke probability where context permits;
- serious safety/law/accident/harm/incident topics suppress humor;
- natural Russian editorial voice without the legacy excessive-profanity instruction.

## CI regression — closed

Run #951 failed at the regression gate because two image-hardening tests mocked `extract_image_candidates()` as a list instead of the real `(ranked_candidates, final_url)` tuple.

Fixed in `5415478c418263ab3e8233ff731584a90b5ee198`.

A dedicated non-production `Intily Regression Gate` now runs on push/PR. Run #2 passed **49/49 tests** on the latest media-caption correction.

## Production run #953

Run #953 completed successfully and proved:

- 49 regression tests passed;
- Groq runtime override loaded: `openai/gpt-oss-20b`;
- publication interval override loaded: `180` seconds;
- joke rate override loaded: `0.8`;
- clean editor prompt override loaded;
- Gemini successfully processed live candidates;
- Telegram publication succeeded: `TELEGRAM_SENT 1135`;
- `BUSINESS_RESULT PUBLISHED telegram_delivery_ok`;
- `QUEUE_SCORE_AUDIT invariant_ok:true`;
- state and analytics persisted.

## Media diagnosis from #953

The image subsystem reached a real image payload:

`IMAGE_PAYLOAD_BYTES 41356 source_bytes 41356 optimized False`

The image itself was therefore not blocked by source access, MIME, dimensions or Telegram payload size.

The final failure was:

`IMAGE_FALLBACK_TEXT PHOTO_CAPTION_LIMIT_TEXT_FALLBACK`

So #953 did **not** prove photo delivery, but it did prove that the prior image extraction/validation work can obtain a usable image in production.

## Media correction deployed after #953

The runtime editor prompt was tightened to approximately 350 characters so that the complete editorial post can fit within Telegram's photo-caption limit while remaining one message.

Commit: `5f9a49ac83063957398c8267b124060e1d4fc00e`.

Regression Gate run #2 passed after this correction.

### Required next evidence

A new production run must show:

`IMAGE_FOUND` → `IMAGE_VALIDATED` → `TELEGRAM_PHOTO_SENT`

If caption length still blocks delivery, do not silently truncate the editorial text. Implement a structural photo/text delivery strategy instead.

## Editor prompt correction

Inspection exposed a legacy `build_edit_prompt()` that instructed an unsuitable character and excessive profanity. Production runtime now overrides it with a factual, natural Russian editorial prompt and controlled humor.

Run #953 proves the override loaded successfully.

## Groq gate

The retired `llama-3.1-8b-instant` caused the historical `404 svgmodel_not_found`. Current runtime is `openai/gpt-oss-20b`.

Run #953 used Gemini for all live editorial requests, so Groq fallback remains unproven.

Closure evidence:

`AI_PROVIDER_ATTEMPT GROQ` → `AI_PROVIDER_OK GROQ`

or a bounded correctly classified Groq failure.

## Scheduler / cadence

GitHub Actions is `workflow_dispatch` only. Cloudflare is the production scheduler.

Current versioned worker: `* * * * *` UTC with a 1/3 dispatch gate. This is probabilistic dispatch, not a guaranteed 3- or 5-minute cadence. Several consecutive production runs are required for cadence confirmation.

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

1. Real Groq fallback proof.
2. Real photo publication proof after the 350-character correction.
3. Several consecutive successful scheduler-dispatched cycles.
4. Cadence confirmation.

## Final assessment

**80% — YELLOW. Production-capable, not yet fully GREEN.**

Acceptance rule:

**fact → root cause → implementation → tests → real production run → telemetry inspection → documentation.**

A commit or green unit test is never production proof by itself.
