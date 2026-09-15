# INTILY — Production Changelog — 2026-09-15 — Free AI Router

## Incident

Production runs were executing, but publication halted because the configured AI providers were exhausted/unavailable. The immediate evidence was Groq HTTP 429 daily token quota while Gemini/OpenAI were already circuit-blocked.

The previous automatic recovery only inspected persisted circuit state. That was insufficient because a provider can have no persisted circuit flag and still be unavailable due a live daily quota response.

## Decision

Adopt a **free-first AI routing policy** without changing the editorial prompt or Telegram publication contract.

### Changes

1. AI editorial evaluations per production cycle are capped at **2** instead of 10.
   - Deterministic scoring continues to rank the queue first.
   - Only the top publication candidates reach the AI editor.
   - `MAX_PUBLISH` remains 1.
   - This is a throughput/quota optimization only; editorial behavior is unchanged.

2. Added `scripts/intily_free_ai_router.py`.
   - Provider order: Gemini → Groq → OpenRouter Free → OpenAI.
   - OpenRouter uses `openrouter/free`, which is a $0-token router over currently available free models.
   - OpenRouter is optional and activates only when `OPENROUTER_API_KEY` exists.
   - No unedited fallback is allowed.

3. Added quota-aware circuit classification.
   - Daily quota/credits exhaustion gets a long cooldown.
   - Short 429 rate limits are treated as transient.
   - Provider state is persisted; queue and published history are untouched.

4. Extended `scripts/intily_provider_recovery.py` to include OpenRouter.

5. Production workflow now runs the free-first wrapper and exposes an optional `OPENROUTER_API_KEY` secret.

6. Added regression coverage in `scripts/test_intily_free_ai_router.py`.

## External verification

Google currently documents `gemini-3.1-flash-lite` as a cost-efficient, high-volume model and lists a Free Tier with $0 input/output pricing. urlGemini model documentationhttps://ai.google.dev/gemini-api/docs/models

OpenRouter currently documents `openrouter/free` as a $0-token router over free models. Its official documentation also states that a free account is limited to 50 requests/day and 20 requests/minute, so it is an **emergency fallback, not the primary 5-minute production provider**. urlOpenRouter Free Models Routerhttps://openrouter.ai/openrouter/free/

GitHub Models was checked and is not a viable fallback: GitHub's current documentation says the service was fully retired on July 30, 2026. urlGitHub Models retirement noticehttps://docs.github.com/en/github-models

## Acceptance criteria

A production fix is accepted only after a fresh workflow run proves one of:

- `AI_PROVIDER_OK GEMINI` + `TELEGRAM_SENT` / `TELEGRAM_PHOTO_SENT` + `BUSINESS_RESULT PUBLISHED telegram_delivery_ok`;
- `AI_PROVIDER_OK GROQ` + successful Telegram delivery;
- `AI_PROVIDER_OK OPENROUTER` + successful Telegram delivery.

Commit/CI success alone is not production proof.

## User action

The OpenRouter fallback is fully implemented in code. If `OPENROUTER_API_KEY` is not already present in GitHub Actions secrets, one manual secret addition is required before that fallback can operate. No payment is required for the OpenRouter free model tier itself.
