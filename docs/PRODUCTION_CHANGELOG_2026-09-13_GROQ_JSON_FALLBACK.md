# INTILY Production Changelog — 2026-09-13 — Groq JSON fallback

## Incident

Production cycles #1201, #1202 and #1203 completed as GitHub Actions runs but published **0 Telegram posts**. The durable queue was not empty; it contained high-scoring candidates.

## Verified evidence

### Run #1201

- GitHub run: `34756646264`
- publisher started with a fresh candidate set and successfully used Gemini for several evaluations.
- Gemini then returned HTTP 503 (`This model is currently experiencing high demand`).
- Groq was attempted as failover and returned HTTP 400 with `json_valid`: `Failed to validate JSON` / `Failed to generate JSON`.
- OpenAI was already circuit-open because the account had no usable quota.
- Result: `PUBLICATION_HALTED provider_runtime_unavailable`, `published=0`.
- Importantly, the run discovered **565 raw items, 14 candidates and added 6 new materials to the durable queue**. Therefore this was not a lack-of-news incident.

### Run #1202

- GitHub run: `34756828374`
- queue contained 18 items.
- Gemini first timed out, then temporarily recovered and evaluated one candidate, but subsequent Gemini calls timed out again.
- Groq repeatedly returned HTTP 400 `json_valid` errors.
- OpenAI remained circuit-open.
- Result: `PUBLICATION_HALTED provider_runtime_unavailable`, `published=0`.

### Run #1203

- GitHub run: `34757005998`
- queue contained 18 items.
- Gemini first timed out and then returned HTTP 503.
- Groq returned HTTP 400 `json_valid` / `Failed to generate JSON` on both attempts.
- OpenAI remained circuit-open.
- Result: `PUBLICATION_HALTED provider_runtime_unavailable`, `published=0`.

### Run #1204

- GitHub run: `34757186317`
- completed successfully and restored Telegram publication.
- This confirms that the publisher, queue and Telegram path were not globally broken; the immediate blocker was provider availability/failover robustness.

## Root cause

The concrete failure chain was:

`Gemini transient timeout/503 → Groq fallback → Groq JSON Object Mode HTTP 400 → OpenAI unavailable → provider_runtime_unavailable → no publication`

The previous Groq hardening changed deprecated parameters and added JSON Object Mode, but the live evidence shows that JSON Object Mode itself can reject this production prompt with HTTP 400. The previous fix therefore improved the API contract but did not close the actual production failure mode.

Official Groq documentation confirms that JSON Object Mode can error and recommends Structured Outputs when supported. GPT-OSS 20B supports structured output, while JSON Object Mode remains a best-effort JSON mechanism.

## Corrective action

Commit `5ea3a424e72f87e333d39894b0a90a79c99149a6` changes the canonical production entrypoint:

1. Keep `max_completion_tokens` and `include_reasoning=false` for GPT-OSS.
2. Attempt the existing JSON Object Mode first.
3. If Groq returns the observed JSON-generation HTTP 400 (`json_valid`, `failed to generate JSON`, `failed to validate JSON`), retry the same editorial request without `response_format`.
4. Validate the returned text locally and extract a JSON object if the model wraps it in prose.
5. Apply the same plain-text fallback when the first JSON-mode response is empty/invalid.
6. Quota, Cloudflare 1010 and other non-retryable failures remain non-retryable.

Regression coverage was added in commit `9a12eaacf79b963fd5f42171d718a9dc1c3a0cfa` for:

- JSON-mode 400 → plain-text JSON fallback;
- empty JSON-mode response → plain-text JSON fallback;
- existing quota and Cloudflare 1010 behavior.

## Verification status

- Code commits are complete.
- Fresh live proof of the new Groq fallback is still required. A commit is **not** production evidence.
- The next production run must show either:
  - `GROQ_JSON_MODE_FALLBACK_TEXT` followed by `GROQ_JSON_TEXT_FALLBACK_OK`, then `EDITORIAL_QA_OK` and `TELEGRAM_SENT`; or
  - a successful Gemini path followed by `TELEGRAM_SENT`.

## Scope protection

No editorial prompt, `style_prompt`, queue retention, Telegram destination, media policy or live Cloudflare Worker was changed by this incident fix.
