# INTILY — Final Production Audit — 2026-09-11

## Executive status

**Overall readiness: 90% — YELLOW / final production verification.**

Core publication is proven end-to-end. Production run #1018 completed successfully, and the dedicated Regression Gate is now independently green after the CI isolation fix: **50 tests passed** on commit `8c8b52d18705b1085a08b1d3a0fe5559844bfeb5`.

The previous Pillow incident is now clarified by facts: production run #1018 installed **Pillow 12.3.0** and all 50 tests passed. Therefore Pillow 12.3.0 was not proven to be the cause of the earlier regression-gate interruption. The durable fix is to remove Pillow from regression fixture generation entirely and isolate Regression Gate triggers from production state commits.

The previously introduced runtime editorial override has been removed. The user's prompt in `scripts/intily_ai_news.py` is canonical and must not be changed or overridden without explicit approval.

## CI reliability — GREEN

Regression Gate commit `8c8b52d18705b1085a08b1d3a0fe5559844bfeb5` produced check run `103159366568` / Actions run `34566421454` with:

- `status=completed`;
- `conclusion=success`;
- **50 tests in 0.555s — OK**;
- no Pillow installation step;
- deterministic stdlib-only image fixtures.

The workflow now uses path filters for `scripts/**` and its own workflow. Production state/analytics writes under `data/**` no longer start regression CI. This is the architectural correction for CI coupling/churn.

## Production run #1018

Run #1018 completed successfully with the production workflow:

- production media runtime installed **Pillow 12.3.0** successfully;
- all 50 regression tests passed before publisher execution;
- Gemini successfully processed live candidates;
- Telegram publication succeeded: `TELEGRAM_SENT 1186`;
- `BUSINESS_RESULT PUBLISHED telegram_delivery_ok`;
- `QUEUE_SCORE_AUDIT invariant_ok:true`;
- state and analytics persisted.

This is direct evidence that current production code is compatible with Pillow 12.3.0.

## Historical provider incident — fixed

Run #1002 failed with exit code 124 because a Groq daily/token quota HTTP 429 was incorrectly treated as retryable, causing repeated waits until the outer 240-second timeout.

Fix:

`75cdc250cf3e03546aa4583c74d047a61dfd1a3c`

Regression coverage:

`ae3d283e030f0d27324ec88f1157664608aa5853`

Current regression evidence includes explicit tests that Groq quota 429 and Cloudflare 1010 failures do not retry indefinitely.

## User editorial prompt — canonical

The prompt in `scripts/intily_ai_news.py` remains the user's intentional configuration. The selector is:

- `style_prompt = 1` — original user prompt;
- `style_prompt = 2` — clean/professional alternative.

Technical compatibility layers must not replace the selected editorial prompt.

## Media gate

Run #953 and run #1018 both prove that the image subsystem can obtain a real image payload. Run #1018 reached:

`IMAGE_PAYLOAD_BYTES 85730 source_bytes 85730 optimized False`

The current production guard then rejected the complete photo caption because it exceeded Telegram's 1024-byte caption limit and correctly fell back to the complete text post:

`IMAGE_FALLBACK_TEXT PHOTO_CAPTION_LIMIT_TEXT_FALLBACK`

Editorial text is not truncated.

**Open gate:** real photo delivery telemetry:

`IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT`

## Groq gate

Current technical runtime is `openai/gpt-oss-20b` via a technical-only `sitecustomize.py` override because the historical `llama-3.1-8b-instant` was retired.

Current tests prove bounded quota failure handling. A fresh live fallback after the current hardening is still preferred as final evidence.

## Scheduler / cadence

GitHub Actions is `workflow_dispatch` only. Cloudflare is the production scheduler.

Current versioned worker: `* * * * *` UTC with a 1/3 dispatch gate. This is probabilistic and not a guaranteed 3- or 5-minute cadence.

**Open gate:** several consecutive Cloudflare-dispatched production cycles proving real cadence and no regression between cycles.

## Remaining gates

1. Real photo publication proof without changing the user's editorial prompt.
2. Fresh live Groq fallback proof after retry hardening, or a production bounded failure under quota conditions.
3. Several consecutive scheduler-dispatched production cycles and cadence confirmation.

## Final assessment

**90% — YELLOW. Production-capable and CI-stable; not yet fully GREEN.**

The project is materially closer to the requested 99% state. No further user action is currently required for the CI fix.

Acceptance rule:

**fact → root cause → implementation → tests → real production run → telemetry inspection → documentation.**

A commit or green unit test is never production proof by itself.
