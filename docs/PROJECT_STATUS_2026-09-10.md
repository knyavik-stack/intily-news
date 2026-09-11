# INTILY Project Status — 2026-09-11

## Canonical current status

**🟡 FINAL PRODUCTION VERIFICATION — 92%.** Core publication works end-to-end in successful runs. Production run #1018 completed successfully. Regression Gate is independently green with 50 tests. Media caption handling has now been hardened so editorial text is never truncated. Remaining work is live production proof for the new photo+full-text path, current Groq fallback behavior, and scheduler cadence.

Production contract:

`Cloudflare intily-ai-news scheduler → GitHub Actions workflow_dispatch → Python production entrypoint → Telegram @intily → durable GitHub state`

Telegram posts contain **editorial content only**. Queue statistics, queue-next information and operational diagnostics remain disabled (`SHOW_QUEUE_DIAGNOSTICS = False`).

## CI incident — Regression Gate #17–#21 — CLOSED

The user observed that after Regression Gate runs #17–#19 the production `Intily AI News Publisher` Actions stopped executing normally. Gates #20 and #21 became executable again after the user manually changed the regression workflow to `Pillow<10.0.0`.

The exact historical #17–#19 failure chain is not falsely attributed to Pillow without their logs. What is factually established is:

- production run #1018 installed **Pillow 12.3.0**;
- production then passed **all 50 regression tests**;
- the regression suite did not need Pillow for its fixture contract;
- Regression Gate previously ran on production state/analytics pushes, creating unnecessary CI coupling/churn.

Durable fix:

- deterministic stdlib-only image fixtures;
- no Pillow installation in Regression Gate;
- `paths` filters for `scripts/**` and the regression workflow;
- production `data/**` writes do not start regression CI.

Verified baseline:

- commit `8c8b52d18705b1085a08b1d3a0fe5559844bfeb5`;
- check run `103159366568`;
- Actions run `34566421454`;
- **50/50 passed** in 0.555s.

## Latest production verification — run #1018

Run #1018 completed successfully:

- production workflow `success`;
- media runtime installed **Pillow 12.3.0**;
- 50 regression tests passed before publisher execution;
- Gemini processed live editorial candidates;
- `TELEGRAM_SENT 1186`;
- `BUSINESS_RESULT PUBLISHED telegram_delivery_ok`;
- `QUEUE_SCORE_AUDIT invariant_ok:true`;
- state/analytics persistence succeeded.

## Latest production reliability incident — run #1002 — FIXED

Run #1002 failed with exit code **124** because a Groq daily/token quota HTTP 429 was incorrectly treated as retryable. The runtime now classifies that failure correctly and bounds provider retries.

Fix: `75cdc250cf3e03546aa4583c74d047a61dfd1a3c`.
Regression coverage: `ae3d283e030f0d27324ec88f1157664608aa5853`.

## User editorial prompt — canonical rule

The user-authored prompt in `scripts/intily_ai_news.py` remains canonical and selectable through `style_prompt`:

- `style_prompt = 1` — original user prompt;
- `style_prompt = 2` — clean/professional alternative.

No technical runtime layer may replace the selected editorial prompt without explicit approval.

## Media gate — hardened, live proof pending

Runs #953 and #1018 proved that publisher-first image retrieval can obtain real image payloads.

The old behavior rejected an image when the complete editorial text exceeded Telegram's 1024-byte photo-caption limit. The new behavior is:

- ≤1024 bytes: `sendPhoto` with the complete caption;
- >1024 bytes: `sendPhoto` with empty caption, then the **complete unchanged editorial text** through the existing Telegram text sender;
- image failure: complete text fallback.

No editorial text is truncated.

Expected telemetry for the split path:

`IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT → TELEGRAM_FULL_TEXT_SENT_AFTER_PHOTO`

Regression coverage was added for this behavior. **Live production proof remains open.**

## Provider gate

Failover order remains:

1. Gemini — primary;
2. Groq `openai/gpt-oss-20b` — fallback;
3. OpenAI — fallback if key/quota is available.

Current tests prove bounded Groq quota handling. Fresh live fallback evidence remains open.

## Scheduler / cadence

GitHub Actions uses `workflow_dispatch` only. Cloudflare is the production scheduler.

The versioned worker uses `* * * * *` UTC with a 1/3 dispatch gate. This is probabilistic, not a guaranteed 3- or 5-minute cadence.

## Current gates

### 🟢 GREEN

- Cloudflare → GitHub Actions → Python → Telegram architecture;
- Gemini primary;
- Telegram text delivery;
- durable state;
- queue/dedup/final-score invariant;
- canonical user editorial prompt;
- image retrieval/validation reached real payloads;
- provider retry hardening implemented and regression-tested;
- historical Regression Gate baseline 50/50 green;
- production run #1018 successful;
- Pillow 12.3.0 proven compatible with production test/runtime path;
- no-truncation media split behavior implemented and unit-tested.

### 🟡 YELLOW / OPEN

- fresh Regression Gate after media split change;
- real photo-send proof with `TELEGRAM_PHOTO_SENT`;
- fresh live Groq fallback proof;
- several consecutive Cloudflare-dispatched cycles;
- cadence confirmation.

### 🔴 RED

No known critical architecture blocker.

## Acceptance rule

**fact → root cause → implementation → tests → real production run → telemetry inspection → documentation.**

Commit/CI success alone is never production proof.
