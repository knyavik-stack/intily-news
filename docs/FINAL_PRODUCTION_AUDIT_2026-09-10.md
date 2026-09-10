# INTILY — Final Production Audit — 2026-09-10

## Executive status

**Overall readiness: 80% — YELLOW / production verification mode.**

Core publication is proven end-to-end. CI regression was fixed. Production run #953 proved successful text publication. The media investigation advanced materially: #953 obtained a real 41 KB image payload, but photo delivery was blocked by the Telegram caption-length guard.

The previously introduced runtime editorial override has been removed. The user's prompt in `scripts/intily_ai_news.py` is canonical and must not be changed or overridden without explicit approval.

## Product contract

Telegram posts contain **editorial content only**. Queue statistics, queue-next information and operational diagnostics are disabled in posts.

`SHOW_QUEUE_DIAGNOSTICS = False`

## CI regression — closed

Run #951 failed at the regression gate because two image-hardening tests mocked `extract_image_candidates()` as a list instead of the real `(ranked_candidates, final_url)` tuple.

Fixed in `5415478c418263ab3e8233ff731584a90b5ee198`.

A dedicated non-production `Intily Regression Gate` now runs on push/PR. The corrected publisher passed the latest regression run.

## Production run #953

Run #953 completed successfully and proved:

- 49 regression tests passed;
- technical Groq runtime migration loaded: `openai/gpt-oss-20b`;
- Gemini successfully processed live candidates;
- Telegram publication succeeded: `TELEGRAM_SENT 1135`;
- `BUSINESS_RESULT PUBLISHED telegram_delivery_ok`;
- `QUEUE_SCORE_AUDIT invariant_ok:true`;
- state and analytics persisted.

The run also contained logs for publication-interval, joke-rate and editor-prompt runtime overrides. Those overrides were not authorized product policy and have now been removed from `scripts/sitecustomize.py`.

## User editorial prompt — canonical

The prompt around line 1345 of `scripts/intily_ai_news.py` is the user's intentional configuration. Its tone, profanity, humor target and approximately 700-character target are part of the requested editorial behavior and remain unchanged.

A manual switch is now available near the beginning of the file:

- `style_prompt = 1` — the user's original hard/maternal/sarcastic prompt;
- `style_prompt = 2` — the additional clean/professional Russian prompt without profanity.

The selected prompt is the only editorial prompt passed to the AI editor. Invalid values fail explicitly.

**Rule:** technical defects may be fixed autonomously; user-authored editorial behavior requires explicit approval before modification or runtime override.

## Media diagnosis from #953

The image subsystem reached a real image payload:

`IMAGE_PAYLOAD_BYTES 41356 source_bytes 41356 optimized False`

The image itself was therefore not blocked by source access, MIME, dimensions or Telegram payload size.

The final failure was:

`IMAGE_FALLBACK_TEXT PHOTO_CAPTION_LIMIT_TEXT_FALLBACK`

So #953 did **not** prove photo delivery, but it did prove that the image extraction/validation work can obtain a usable image in production.

The earlier attempt to force an approximately 350-character editorial prompt has been removed. Do not shorten or alter the user's editorial prompt to solve this technical limitation.

### Required next evidence

A new production run must show:

`IMAGE_FOUND` → `IMAGE_VALIDATED` → `TELEGRAM_PHOTO_SENT`

If caption length blocks delivery, implement a structural media/text delivery strategy that preserves the complete editorial content rather than silently truncating or rewriting it.

## Groq gate

The retired `llama-3.1-8b-instant` caused the historical `404 svgmodel_not_found`. Current technical runtime is `openai/gpt-oss-20b`.

Run #953 used Gemini for all live editorial requests, so Groq fallback remains unproven.

Closure evidence:

`AI_PROVIDER_ATTEMPT GROQ` → `AI_PROVIDER_OK GROQ`

or a bounded correctly classified Groq failure.

## Scheduler / cadence

GitHub Actions is `workflow_dispatch` only. Cloudflare is the production scheduler.

Current versioned worker: `* * * * *` UTC with a 1/3 dispatch gate. This is probabilistic dispatch, not a guaranteed 3- or 5-minute cadence. Several consecutive production runs are required for cadence confirmation.

## Remaining gates

1. Real Groq fallback proof.
2. Real photo publication proof without changing the user's editorial prompt.
3. Several consecutive successful scheduler-dispatched cycles.
4. Cadence confirmation.

## Final assessment

**80% — YELLOW. Production-capable, not yet fully GREEN.**

Acceptance rule:

**fact → root cause → implementation → tests → real production run → telemetry inspection → documentation.**

A commit or green unit test is never production proof by itself.
