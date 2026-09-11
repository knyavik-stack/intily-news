# INTILY Project Status — 2026-09-11

## Canonical current status

**🟡 FINAL PRODUCTION VERIFICATION — 94%.** Core publication works end-to-end in successful runs. Production runs #1047 and #1062 completed successfully with live editorial processing; #1047 proved real image retrieval and Telegram photo delivery, while #1062 proved the current no-orphan policy code passes the full 53-test preflight and remains operational in production. The media caption policy is hardened so posts exceeding Telegram's 1024-character photo-caption limit are published as one complete text-only post rather than an orphan image plus a second text message. Regression Gate #35 is green with **53 tests** on the corrected media policy. Remaining work is fresh live proof of both media branches, fresh live Groq fallback evidence, and several consecutive Cloudflare-dispatched cycles/cadence confirmation.

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

## Latest production verification — run #1062

Run #1062 completed successfully on commit `c1922b4520b639e7f71602a67eb8909dee87f3de` before the subsequent analytics persistence commit.

Verified from the production job log:

- media runtime installed **Pillow 12.3.0**;
- the production preflight ran **53/53 tests successfully**;
- `GROQ_MODEL_RUNTIME_OVERRIDE openai/gpt-oss-20b` loaded only as technical compatibility migration;
- Gemini successfully edited a live candidate;
- Telegram publication emitted `TELEGRAM_SENT 1230`;
- `BUSINESS_RESULT PUBLISHED telegram_delivery_ok`;
- `QUEUE_SCORE_AUDIT invariant_ok:true`;
- state/analytics persistence succeeded and advanced `main` to `6f35e9f`.

The selected item in #1062 did **not** exercise the no-orphan long-caption branch: its image path fell back because `ARTICLE_SOURCE_UNRESOLVED`. Therefore #1062 is proof that the current production policy remains operational, not proof of the long-caption branch itself.

## Latest ordinary image verification — run #1047

Run #1047 completed successfully and proved the ordinary image path:

- production workflow `success`;
- media runtime installed **Pillow 12.3.0**;
- live editorial candidate processed successfully;
- real image was found and validated;
- `TELEGRAM_PHOTO_SENT` was emitted;
- `TELEGRAM_SENT` and `BUSINESS_RESULT PUBLISHED telegram_delivery_ok` were emitted;
- `QUEUE_SCORE_AUDIT invariant_ok:true`;
- state/analytics persistence succeeded.

## Production run #1048 — CLOSED AS STALE-CODE FAILURE

Run #1048 was started from commit `b4ddc428f517dbfc5dfdc2889bac61371c9c5d3b`, before the regression-test update. Its policy/analytics check failed because it still expected the old `photo_plus_full_text` behavior. The log explicitly shows the assertion mismatch and then the state was persisted successfully. It did **not** execute the news engine.

This is not evidence of a failure in the current `main`: Regression Gate #35 subsequently checked commit `cc0fee92747d99b6a08cce25aebe849946a8a0eb` and passed 53/53.

## Latest production reliability incident — run #1002 — FIXED

Run #1002 failed with exit code **124** because a Groq daily/token quota HTTP 429 was incorrectly treated as retryable. The runtime now classifies that failure correctly and bounds provider retries.

Fix: `75cdc250cf3e03546aa4583c74d047a61dfd1a3c`.
Regression coverage: `ae3d283e030f0d27324ec88f1157664608aa5853`.

## User editorial prompt — canonical rule

The user-authored prompt in `scripts/intily_ai_news.py` remains canonical and selectable through `style_prompt`:

- `style_prompt = 1` — original user prompt;
- `style_prompt = 2` — clean/professional alternative.

No technical runtime layer may replace the selected editorial prompt without explicit approval.

## Media gate — no-orphan-image policy

Runs #953, #1018, #1025 and #1047 proved that publisher-first image retrieval can obtain real image payloads and that Telegram photo delivery works.

Telegram Bot API specifies **0–1024 characters after entities parsing** for `sendPhoto` captions. This is a character limit, not a UTF-8 byte limit. The runtime caption guard therefore counts visible characters after Telegram-style HTML sanitization/entity decoding.

Current production media policy:

- **≤1024 visible caption characters:** send the image with the complete editorial text as the photo caption;
- **>1024 visible caption characters:** do **not** send the image separately; publish the complete unchanged editorial text once through the normal Telegram text sender;
- image retrieval/validation/delivery failure: publish the complete text fallback;
- editorial text is never truncated and an orphan image is never intentionally published.

The no-orphan behavior is implemented in the audience/media policy layer and is regression-tested. Commit: `b4ddc428f517dbfc5dfdc2889bac61371c9c5d3b`.

Regression coverage was updated in commit `cc0fee92747d99b6a08cce25aebe849946a8a0eb` and **53/53 passed** in Regression Gate #35 (`34592272934`).

Expected telemetry for a same-message photo post:

`IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT` with no `TELEGRAM_FULL_TEXT_SENT_AFTER_PHOTO`.

Expected telemetry for a long post:

`IMAGE_SKIPPED_CAPTION_LIMIT → TELEGRAM_SENT` with no `TELEGRAM_PHOTO_SENT` and no second text message.

**Fresh live production proof of the exact long-caption no-orphan branch remains open.**

Detailed incident/fix record: `docs/PRODUCTION_CHANGELOG_2026-09-11_MEDIA_CAPTION_POLICY.md`.

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
- Regression Gate #35 **53/53 green**;
- production runs #1047 and #1062 successful;
- Pillow 12.3.0 proven compatible with production test/runtime path;
- no-orphan media policy implemented and regression-tested;
- Telegram caption limit handled as characters, not bytes.

### 🟡 YELLOW / OPEN

- fresh production proof that a valid ≤1024-character Russian editorial post stays attached to the photo as one Telegram message;
- fresh production proof that a >1024-character post produces text only with no orphan image;
- fresh live Groq fallback proof;
- several consecutive Cloudflare-dispatched cycles;
- cadence confirmation.

### 🔴 RED

No known critical architecture blocker.

## Acceptance rule

**fact → root cause → implementation → tests → real production run → telemetry inspection → documentation.**

Commit/CI success alone is never production proof.
