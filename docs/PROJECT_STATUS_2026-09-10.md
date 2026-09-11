# INTILY Project Status — 2026-09-11

## Canonical current status

**🟡 FINAL PRODUCTION VERIFICATION — 94%.** Core publication works end-to-end in successful runs. Production run #1018 completed successfully and run #1025 proved real image retrieval, validation and Telegram photo delivery. The media caption guard has now been corrected to Telegram's actual 1024-character limit. Regression Gate #32 is green with 52 tests. Remaining work is a fresh production run on the corrected caption logic, fresh live Groq fallback evidence, and several consecutive Cloudflare-dispatched cycles/cadence confirmation.

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

## Latest production verification — run #1025

Run #1025 completed successfully and proved the existing media transport path:

- production workflow `success`;
- media runtime installed **Pillow 12.3.0**;
- 51 regression tests passed before publisher execution;
- Gemini processed the live editorial candidate;
- `IMAGE_FOUND og_image 1200 630`;
- `IMAGE_VALIDATED image/jpeg 274452`;
- `TELEGRAM_PHOTO_SENT 1192`;
- `TELEGRAM_SENT 1193`;
- `TELEGRAM_FULL_TEXT_SENT_AFTER_PHOTO`;
- `BUSINESS_RESULT PUBLISHED telegram_delivery_ok`;
- `QUEUE_SCORE_AUDIT invariant_ok:true`;
- state/analytics persistence succeeded.

This run showed that the image itself was successfully published, but the photo and full editorial text were sent as two Telegram messages. That is the behavior currently being corrected.

## Latest production reliability incident — run #1002 — FIXED

Run #1002 failed with exit code **124** because a Groq daily/token quota HTTP 429 was incorrectly treated as retryable. The runtime now classifies that failure correctly and bounds provider retries.

Fix: `75cdc250cf3e03546aa4583c74d047a61dfd1a3c`.
Regression coverage: `ae3d283e030f0d27324ec88f1157664608aa5853`.

## User editorial prompt — canonical rule

The user-authored prompt in `scripts/intily_ai_news.py` remains canonical and selectable through `style_prompt`:

- `style_prompt = 1` — original user prompt;
- `style_prompt = 2` — clean/professional alternative.

No technical runtime layer may replace the selected editorial prompt without explicit approval.

## Media gate — caption-limit correction, live proof pending

Runs #953, #1018 and #1025 proved that publisher-first image retrieval can obtain real image payloads and that Telegram photo delivery works.

The previous guard incorrectly treated Telegram's photo-caption limit as 1024 UTF-8 bytes. Telegram Bot API specifies **0–1024 characters after entities parsing** for `sendPhoto` captions. This distinction is material for Russian text because UTF-8 byte length is larger than character count.

The production guard was corrected in `c446d916647953bcc679ba4e0d7a6d0abc31b26e` and regression coverage was added. Regression Gate #32 (`34571826952`) passed **52/52** tests on commit `e19a01e6bbb481d7b385acb5573ddcff7b794fe4`.

Current behavior:

- ≤1024 visible Telegram caption characters: `sendPhoto` with the complete caption;
- >1024 visible characters: `sendPhoto` with empty caption, then the **complete unchanged editorial text** through the existing Telegram text sender;
- image failure: complete text fallback.

No editorial text is truncated.

Expected telemetry for a same-message photo post:

`IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT` with no `TELEGRAM_FULL_TEXT_SENT_AFTER_PHOTO`.

For a genuinely >1024-character post, a single Telegram photo message cannot carry the entire editorial text as its caption; the split behavior remains the safe no-truncation fallback.

Detailed incident/fix record: `docs/PRODUCTION_CHANGELOG_2026-09-11_MEDIA_CAPTION_FIX.md`.

**Fresh live production proof on the corrected caption logic remains open.**

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
- real Telegram photo delivery reached in production;
- provider retry hardening implemented and regression-tested;
- Regression Gate #32 **52/52 green**;
- production run #1018 successful;
- production run #1025 successfully delivered image + text;
- Pillow 12.3.0 proven compatible with production test/runtime path;
- no-truncation media split behavior implemented and regression-tested;
- Telegram caption limit corrected from bytes to characters.

### 🟡 YELLOW / OPEN

- fresh production proof that a valid ≤1024-character Russian editorial post stays attached to the photo as one Telegram message;
- fresh live Groq fallback proof;
- several consecutive Cloudflare-dispatched cycles;
- cadence confirmation.

### 🔴 RED

No known critical architecture blocker.

## Acceptance rule

**fact → root cause → implementation → tests → real production run → telemetry inspection → documentation.**

Commit/CI success alone is never production proof.
