# INTILY — Final Production Audit — 2026-09-11

## Executive status

**Overall readiness: 92% — YELLOW / final production verification.**

Core publication is proven end-to-end. Production run #1018 completed successfully, and the dedicated Regression Gate is independently green after CI isolation: **50 tests passed** on commit `8c8b52d18705b1085a08b1d3a0fe5559844bfeb5`.

The Pillow incident is clarified by facts: production run #1018 installed **Pillow 12.3.0** and all 50 tests passed. Therefore Pillow 12.3.0 was not proven to be the cause of the earlier regression-gate interruption. The durable fix is to remove Pillow from regression fixture generation and isolate Regression Gate triggers from production state commits.

The user's editorial prompt remains canonical. No runtime layer may replace it without explicit approval.

## CI reliability — GREEN

Regression Gate commit `8c8b52d18705b1085a08b1d3a0fe5559844bfeb5` produced check run `103159366568` / Actions run `34566421454` with:

- `status=completed`;
- `conclusion=success`;
- **50 tests in 0.555s — OK**;
- no Pillow installation step;
- deterministic stdlib-only image fixtures.

The workflow uses path filters for `scripts/**` and its own workflow. Production state/analytics writes under `data/**` do not start regression CI.

## Production run #1018

Run #1018 completed successfully:

- production media runtime installed **Pillow 12.3.0** successfully;
- all 50 regression tests passed before publisher execution;
- Gemini processed live candidates;
- Telegram publication succeeded: `TELEGRAM_SENT 1186`;
- `BUSINESS_RESULT PUBLISHED telegram_delivery_ok`;
- `QUEUE_SCORE_AUDIT invariant_ok:true`;
- state and analytics persisted.

## Historical provider incident — fixed

Run #1002 failed with exit code 124 because a Groq daily/token quota HTTP 429 was incorrectly treated as retryable, causing repeated waits until the outer 240-second timeout.

Fix: `75cdc250cf3e03546aa4583c74d047a61dfd1a3c`.

Regression coverage: `ae3d283e030f0d27324ec88f1157664608aa5853`.

## User editorial prompt — canonical

The selector in `scripts/intily_ai_news.py` remains:

- `style_prompt = 1` — original user prompt;
- `style_prompt = 2` — clean/professional alternative.

Technical compatibility layers must not replace the selected editorial prompt.

## Media gate — implementation hardened, live proof pending

Runs #953 and #1018 proved that the image subsystem can obtain real image payloads. The remaining issue was Telegram's 1024-byte photo-caption limit.

The production media path has now been changed so editorial text is **never truncated**:

- caption ≤1024 → photo + complete caption;
- caption >1024 → validated photo with empty caption + complete original editorial text as a second Telegram message;
- image failure → complete text fallback.

New telemetry for the split path:

`IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT → TELEGRAM_FULL_TEXT_SENT_AFTER_PHOTO`

A regression test covers this split behavior. **Live production proof is still required.**

## Groq gate

Current technical runtime is `openai/gpt-oss-20b` via technical-only `sitecustomize.py`, because `llama-3.1-8b-instant` was retired.

Current tests prove bounded quota failure handling. A fresh live fallback remains final evidence.

## Scheduler / cadence

GitHub Actions is `workflow_dispatch` only. Cloudflare is the production scheduler.

Current versioned worker: `* * * * *` UTC with a 1/3 dispatch gate. This is probabilistic, not a guaranteed 3- or 5-minute cadence.

## Remaining gates

1. Fresh Regression Gate after the media split change.
2. Real photo publication proof with `TELEGRAM_PHOTO_SENT`.
3. Fresh live Groq fallback proof, or production bounded quota failure evidence.
4. Several consecutive Cloudflare-dispatched production cycles and cadence confirmation.

## Final assessment

**92% — YELLOW. Production-capable, CI-stable, media behavior hardened; live verification remains.**

Acceptance rule:

**fact → root cause → implementation → tests → real production run → telemetry inspection → documentation.**

A commit or green unit test is never production proof by itself.
