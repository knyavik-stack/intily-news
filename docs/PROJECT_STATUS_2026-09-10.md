# INTILY Project Status — 2026-09-10

## Canonical current status

**🟡 PRODUCTION VERIFICATION MODE — CI reliability hardening in progress.** Core publication works end-to-end in successful runs, and production run #1018 completed successfully. The latest engineering incident was not a publisher outage: the dedicated Regression Gate became noisy/coupled to production state commits, while its test fixture unnecessarily depended on Pillow. This has now been structurally removed from the regression gate; fresh CI verification is required.

Production contract:

`Cloudflare intily-ai-news scheduler → GitHub Actions workflow_dispatch → Python production entrypoint → Telegram @intily → durable GitHub state`

Telegram posts contain **editorial content only**. Queue statistics, queue-next information and operational diagnostics remain disabled (`SHOW_QUEUE_DIAGNOSTICS = False`).

## CI incident — Regression Gate #17–#21

The user observed that after Regression Gate runs #17–#19 the production `Intily AI News Publisher` Actions stopped executing normally. Gates #20 and #21 became executable again after the user manually changed the regression workflow to `Pillow<10.0.0`.

The previous regression workflow installed `Pillow>=11,<13` even though the regression tests only needed Pillow to manufacture test images. This made CI dependent on an external imaging-library API/version that is not part of the regression contract. The production workflow is a separate runtime and successfully completed run #1018.

A blind permanent Pillow downgrade is **not** the accepted fix. Instead:

- `scripts/test_intily_image_runtime.py` now creates deterministic PNG fixtures using only Python stdlib (`hashlib`, `struct`, `zlib`);
- `.github/workflows/intily-regression.yml` no longer installs Pillow at all;
- the regression gate now uses `paths` filters for `scripts/**` and its own workflow, so production state/analytics writes under `data/**` do not spawn regression runs;
- production scheduling remains independent of the regression gate.

Commits:

- `ec865255fa8ec534a0304b8893324717ef2370f7` — first dependency-free image fixture implementation;
- `58ae14dc266fd9d0449ee72dee1005d8aaccfc24` — regression path isolation and Pillow removal from workflow;
- `8c8b52d18705b1085a08b1d3a0fe5559844bfeb5` — deterministic >1 MB image fixture correction.

**Verification gate:** a fresh Regression Gate run on `8c8b52d...` must finish green. Until that is observed, CI is not marked GREEN.

GitHub supports combining branch and path filters so a workflow runs only when both conditions match. The current gate uses this to prevent production state-only pushes from starting regression CI.

## Latest production verification — run #1018

Run #1018 completed successfully:

- workflow conclusion: `success`;
- production head: `8b9f47b4b4e9edb7c42f6ac3656206a5e5bf42d0`;
- the production workflow remained `workflow_dispatch` only;
- state/analytics persistence completed.

The production workflow currently installs `Pillow>=11,<13`. This is intentionally separate from the regression fixture dependency and has not been changed based on an unproven assumption.

## Latest production reliability incident — run #1002

Run #1002 failed in the news-engine step and ended with exit code **124**. Root cause was established from the Actions log:

- Gemini temporarily returned HTTP 503;
- Groq returned HTTP 429 with a **tokens-per-day** rate-limit message for `openai/gpt-oss-20b`;
- the runtime incorrectly treated that daily/token quota response as retryable and slept before retrying;
- OpenAI was already circuit-blocked;
- the outer `timeout 240s` killed the process.

Fix deployed in `75cdc250cf3e03546aa4583c74d047a61dfd1a3c` and regression coverage in `ae3d283e030f0d27324ec88f1157664608aa5853`.

## User editorial prompt — canonical rule

The user-authored prompt in `scripts/intily_ai_news.py` remains canonical and selectable through `style_prompt`:

- `style_prompt = 1` — original user prompt;
- `style_prompt = 2` — clean/professional alternative.

No technical runtime layer may replace the selected editorial prompt without explicit approval.

## Media gate

Run #953 proved that publisher-first image retrieval can obtain a real usable image:

`IMAGE_PAYLOAD_BYTES 41356 source_bytes 41356 optimized False`

The remaining blocker was the Telegram photo-caption limit. Production intentionally rejects over-limit captions instead of truncating editorial content.

**Open production evidence:** `IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT` in a real run.

## Provider gate

Failover order remains:

1. Gemini — primary;
2. Groq `openai/gpt-oss-20b` — fallback;
3. OpenAI — fallback if key/quota is available.

A successful live Groq fallback remains unproven, but daily quota failures are now bounded and non-retryable.

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
- image retrieval/validation reached a real payload;
- provider retry hardening implemented;
- production run #1018 successful.

### 🟡 YELLOW / OPEN

- fresh Regression Gate after CI dependency/isolation fix;
- real Groq fallback proof;
- real photo-send proof;
- several consecutive Cloudflare-dispatched cycles;
- cadence confirmation.

### 🔴 RED

No known critical architecture blocker.

## Acceptance rule

**fact → root cause → implementation → tests → real production run → telemetry inspection → documentation.**

Commit/CI success alone is never production proof.
