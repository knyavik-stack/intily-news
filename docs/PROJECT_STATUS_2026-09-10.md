# INTILY Project Status — 2026-09-10

## Canonical current status

**🟡 PRODUCTION VERIFICATION MODE.** Core publication works end-to-end. The latest CI regression was fixed and production run #953 proved successful text publication. The image pipeline reached a real 41 KB image, but photo delivery was blocked by Telegram caption length. The previously added runtime editorial override has now been removed: the user-authored prompt in `scripts/intily_ai_news.py` is canonical and is not to be changed or overridden without explicit approval.

Production contract:

`Cloudflare intily-ai-news scheduler → GitHub Actions workflow_dispatch → Python production entrypoint → Telegram @intily → durable GitHub state`

Telegram posts contain **editorial content only**. Queue statistics, queue-next information and operational diagnostics remain disabled (`SHOW_QUEUE_DIAGNOSTICS = False`).

## Latest CI regression — fixed

Run #951 failed at the regression gate before publisher execution because the two new image-hardening tests mocked `extract_image_candidates()` as a list, while the production contract returns `(ranked_candidates, final_url)`. This caused:

`ValueError: not enough values to unpack (expected 2, got 1)`

Fixed in `5415478c418263ab3e8233ff731584a90b5ee198`.

A dedicated non-production `Intily Regression Gate` was added. Its run #2 completed successfully with **49 tests passed**.

## Latest production verification — run #953

Run #953 completed successfully and proved:

- production regression gate passed: **49 tests**;
- technical Groq runtime migration loaded: `openai/gpt-oss-20b`;
- Gemini processed the live editorial candidates successfully;
- `TELEGRAM_SENT 1135`;
- `BUSINESS_RESULT PUBLISHED telegram_delivery_ok`;
- `QUEUE_SCORE_AUDIT invariant_ok:true`;
- state and analytics persisted.

The earlier run also logged `PUBLISH_INTERVAL_RUNTIME_OVERRIDE`, `JOKE_RATE_RUNTIME_OVERRIDE` and `EDITOR_PROMPT_RUNTIME_OVERRIDE`; those were produced by an unauthorized compatibility override and have now been removed from `scripts/sitecustomize.py`. They are not current production policy.

## User editorial prompt — canonical rule

The prompt beginning in `scripts/intily_ai_news.py` around line 1345 is the user's intentional editorial configuration, including its tone, profanity, humor target and approximately 700-character target. It remains unchanged.

**Rule:** technical defects may be fixed autonomously, but user-authored editorial behavior must not be modified or runtime-overridden without explicit user approval.

## Media finding in #953

The run did **not** fail image extraction. It reached:

`IMAGE_PAYLOAD_BYTES 41356 source_bytes 41356 optimized False`

Then the image stage stopped with:

`IMAGE_FALLBACK_TEXT PHOTO_CAPTION_LIMIT_TEXT_FALLBACK`

The image payload was successfully obtained and was only 41 KB. The blocker was Telegram caption length, not image URL access, MIME, dimensions or payload size.

No 350-character editorial limit is currently deployed. The earlier runtime change that attempted to force such a limit has been removed.

**Open media gate:** solve the caption limit structurally without changing or truncating the user's editorial content, then prove `IMAGE_FOUND` → `IMAGE_VALIDATED` → `TELEGRAM_PHOTO_SENT` in a real production run.

## Groq

Historical evidence showed retired `llama-3.1-8b-instant → 404 → svgmodel_not_found`.

Current technical runtime target is `openai/gpt-oss-20b`.

**Open gate:** real fallback request must show `AI_PROVIDER_ATTEMPT GROQ` + `AI_PROVIDER_OK GROQ`, or a bounded correctly classified failure.

Run #953 used Gemini for all live editorial requests, so it still does not prove Groq fallback.

## Scheduler / cadence

GitHub Actions uses `workflow_dispatch` only. Cloudflare is the scheduler.

The versioned Cloudflare worker uses `* * * * *` UTC with a 1/3 dispatch gate. This is probabilistic dispatch, not a guaranteed 3- or 5-minute interval. Cadence must be confirmed from several real runs.

## Current production gates

### 🟢 GREEN

- Cloudflare → GitHub Actions → Python → Telegram architecture;
- Gemini primary;
- Telegram text delivery;
- durable state;
- queue/dedup/final-score invariant;
- 49-test regression gate;
- user-authored editorial prompt remains canonical;
- image retrieval/validation reached a real 41 KB image in #953.

### 🟡 YELLOW / OPEN

- Groq live fallback proof;
- structural photo delivery and real photo-send proof;
- several consecutive scheduler cycles;
- final cadence confirmation.

### 🔴 RED

No known critical blocker in the core architecture.

## Acceptance rule

**fact → root cause → implementation → tests → real production run → telemetry inspection → documentation.**

Commit or unit-test success alone is never production proof.
