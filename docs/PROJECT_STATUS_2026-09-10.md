# INTILY Project Status — 2026-09-11

## Canonical current status

**🟡 FINAL PRODUCTION VERIFICATION — 90%.** Core publication works end-to-end in successful runs. Production run #1018 completed successfully. The Regression Gate CI incident is now structurally fixed and independently verified green with 50 tests. Remaining work is live production proof for photo delivery, current Groq fallback behavior, and scheduler cadence.

Production contract:

`Cloudflare intily-ai-news scheduler → GitHub Actions workflow_dispatch → Python production entrypoint → Telegram @intily → durable GitHub state`

Telegram posts contain **editorial content only**. Queue statistics, queue-next information and operational diagnostics remain disabled (`SHOW_QUEUE_DIAGNOSTICS = False`).

## CI incident — Regression Gate #17–#21 — CLOSED

The user observed that after Regression Gate runs #17–#19 the production `Intily AI News Publisher` Actions stopped executing normally. Gates #20 and #21 became executable again after the user manually changed the regression workflow to `Pillow<10.0.0`.

The exact historical #17–#19 failure chain is not being falsely attributed to Pillow without their logs. What is now factually established is:

- production run #1018 installed **Pillow 12.3.0**;
- the production workflow then passed **all 50 regression tests**;
- therefore Pillow 12.3.0 is compatible with the current production code/test suite;
- the regression suite did not need Pillow for its runtime contract — it used it only to manufacture image fixtures;
- the Regression Gate also ran on every `main` push, including production state/analytics commits, creating unnecessary CI coupling/churn.

Durable fix:

- `scripts/test_intily_image_runtime.py` now creates deterministic PNG fixtures using only Python stdlib (`hashlib`, `struct`, `zlib`);
- `.github/workflows/intily-regression.yml` no longer installs Pillow;
- Regression Gate uses `paths` filters for `scripts/**` and its own workflow;
- production state/analytics writes under `data/**` no longer spawn regression CI;
- production scheduling remains independent of regression CI.

Verified regression evidence:

- commit: `8c8b52d18705b1085a08b1d3a0fe5559844bfeb5`;
- check run: `103159366568`;
- Actions run: `34566421454`;
- result: **completed / success**;
- tests: **50 / 50 passed** in 0.555s;
- Pillow install step: **absent**.

This closes the CI gate. The user's `Pillow<10.0.0` emergency workaround is no longer needed in Regression Gate and is not being blindly propagated into production.

## Latest production verification — run #1018

Run #1018 completed successfully:

- workflow conclusion: `success`;
- production head: `8b9f47b4b4e9edb7c42f6ac3656206a5e5bf42d0`;
- media runtime installed **Pillow 12.3.0** successfully;
- 50 regression tests passed before publisher execution;
- Gemini processed live editorial candidates;
- Telegram publication succeeded: `TELEGRAM_SENT 1186`;
- `BUSINESS_RESULT PUBLISHED telegram_delivery_ok`;
- `QUEUE_SCORE_AUDIT invariant_ok:true`;
- state/analytics persistence succeeded.

## Latest production reliability incident — run #1002 — FIXED

Run #1002 failed in the news-engine step and ended with exit code **124**. Root cause was established from the Actions log:

- Gemini temporarily returned HTTP 503;
- Groq returned HTTP 429 with a **tokens-per-day** rate-limit message for `openai/gpt-oss-20b`;
- the runtime incorrectly treated that daily/token quota response as retryable and slept before retrying;
- OpenAI was already circuit-blocked;
- the outer `timeout 240s` killed the process.

Fix deployed in `75cdc250cf3e03546aa4583c74d047a61dfd1a3c` and regression coverage in `ae3d283e030f0d27324ec88f1157664608aa5853`.

Current CI explicitly proves that Groq quota 429 does not retry indefinitely.

## User editorial prompt — canonical rule

The user-authored prompt in `scripts/intily_ai_news.py` remains canonical and selectable through `style_prompt`:

- `style_prompt = 1` — original user prompt;
- `style_prompt = 2` — clean/professional alternative.

No technical runtime layer may replace the selected editorial prompt without explicit approval.

## Media gate

Production runs #953 and #1018 proved that publisher-first image retrieval can obtain a real usable image payload:

- #953: `IMAGE_PAYLOAD_BYTES 41356 source_bytes 41356 optimized False`;
- #1018: `IMAGE_PAYLOAD_BYTES 85730 source_bytes 85730 optimized False`.

The remaining blocker is the Telegram photo-caption limit. Production intentionally rejects over-limit captions instead of truncating editorial content and falls back to the complete text post.

**Open production evidence:** `IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT` in a real run.

## Provider gate

Failover order remains:

1. Gemini — primary;
2. Groq `openai/gpt-oss-20b` — fallback;
3. OpenAI — fallback if key/quota is available.

Current tests prove bounded Groq quota handling. A fresh live fallback after the current retry hardening remains preferred final evidence.

## Scheduler / cadence

GitHub Actions uses `workflow_dispatch` only. Cloudflare is the production scheduler.

The versioned worker uses `* * * * *` UTC with a 1/3 dispatch gate. This is probabilistic, not a guaranteed 3- or 5-minute cadence. Several real cycles are required for confirmation.

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
- Regression Gate independently green: 50/50 tests;
- production run #1018 successful;
- Pillow 12.3.0 proven compatible with current production test/runtime path.

### 🟡 YELLOW / OPEN

- real photo-send proof;
- fresh live Groq fallback proof after current hardening, or production bounded quota failure evidence;
- several consecutive Cloudflare-dispatched cycles;
- cadence confirmation.

### 🔴 RED

No known critical architecture blocker.

## Acceptance rule

**fact → root cause → implementation → tests → real production run → telemetry inspection → documentation.**

Commit/CI success alone is never production proof.
