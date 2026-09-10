# INTILY Project Status — 2026-09-10

## Canonical current status

**🟡 PRODUCTION VERIFICATION MODE.** Core publication works end-to-end in successful runs, but the latest production run #1002 exposed a provider-retry timeout defect. The user-authored editorial prompt remains canonical and selectable through `style_prompt`; it is not to be changed or overridden without explicit approval.

Production contract:

`Cloudflare intily-ai-news scheduler → GitHub Actions workflow_dispatch → Python production entrypoint → Telegram @intily → durable GitHub state`

Telegram posts contain **editorial content only**. Queue statistics, queue-next information and operational diagnostics remain disabled (`SHOW_QUEUE_DIAGNOSTICS = False`).

## Latest production incident — run #1002

Run #1002 failed in the news-engine step and ended with exit code **124**. The root cause is now established from the Actions log:

- Gemini temporarily returned HTTP 503 for one candidate and opened its temporary circuit.
- Groq then returned HTTP 429 with a **tokens-per-day** rate-limit message for `openai/gpt-oss-20b`.
- The Groq runtime treated that daily/token quota response as retryable and waited 30 seconds, then retried again.
- OpenAI was already circuit-blocked.
- The publisher subsequently attempted another Gemini/Groq failover path; Groq waited again and the outer `timeout 240s` killed the process.
- GitHub reported: `Process completed with exit code 124`.

This is a **technical retry-classification/budget defect**, not an editorial prompt defect and not a Telegram delivery defect.

### Fix deployed

Commit `75cdc250cf3e03546aa4583c74d047a61dfd1a3c` hardens `scripts/intily_production_entrypoint.py`:

- Groq daily/token quota responses are classified as non-retryable and immediately handed back to provider failover;
- Gemini and Groq request timeouts are bounded by the remaining AI evaluation budget;
- retry sleeps are refused when the remaining AI budget cannot accommodate them;
- Russian comments document the quota behavior.

A regression test was added in `ae3d283e030f0d27324ec88f1157664608aa5853` to prove that a Groq `tokens per day` HTTP 429 causes **one request and no sleep/retry**.

The first regression run after the two sequential commits was cancelled by GitHub because a newer push superseded it; its test step had already completed successfully. The newer Regression Gate run #17 is the authoritative verification run and must finish successfully before the fix is considered CI-proven.

## Latest successful production verification — run #953

Run #953 completed successfully and proved:

- production regression gate passed: **49 tests**;
- technical Groq runtime migration loaded: `openai/gpt-oss-20b`;
- Gemini processed the live editorial candidates successfully;
- `TELEGRAM_SENT 1135`;
- `BUSINESS_RESULT PUBLISHED telegram_delivery_ok`;
- `QUEUE_SCORE_AUDIT invariant_ok:true`;
- state and analytics persisted.

## User editorial prompt — canonical rule

The prompt beginning in `scripts/intily_ai_news.py` around line 1345 is the user's intentional editorial configuration, including its tone, profanity, humor target and approximately 700-character target. It remains unchanged.

The file now has a user-controlled `style_prompt` switch near the publication settings:

- `style_prompt = 1` — the user's original hard/maternal/sarcastic prompt;
- `style_prompt = 2` — an additional clean/professional Russian prompt without profanity;
- only the selected prompt is passed to the AI editor;
- any other value fails explicitly instead of silently selecting a style.

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

The latest run proved that this model can return a 429 daily/token limit. The new code classifies that condition without retrying, but **a successful live fallback request is still unproven**.

**Open gate:** real fallback request must show `AI_PROVIDER_ATTEMPT GROQ` + `AI_PROVIDER_OK GROQ`, or a bounded correctly classified failure without exhausting the workflow timeout.

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
- user-authored editorial prompt remains canonical and is selectable through `style_prompt`;
- image retrieval/validation reached a real 41 KB image in #953;
- provider retry hardening is implemented and covered by regression tests.

### 🟡 YELLOW / OPEN

- Regression Gate #17 completion after retry hardening;
- Groq live fallback proof;
- structural photo delivery and real photo-send proof;
- several consecutive scheduler cycles;
- final cadence confirmation.

### 🔴 RED

No known critical architecture blocker. Run #1002 exposed a bounded technical reliability defect; the corrective code is deployed and awaiting fresh CI + production proof.

## Acceptance rule

**fact → root cause → implementation → tests → real production run → telemetry inspection → documentation.**

Commit or unit-test success alone is never production proof.
