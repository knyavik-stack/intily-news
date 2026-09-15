# INTILY — production changelog — 2026-09-15

## Change

Enforced the free-first AI router's `MAX_AI_EVAL_PER_CYCLE = 2` at the production scoring-runtime guard level.

## Root cause found

Production run #1396 showed:

- `AI_EVALUATION_CAP 2` was printed by `intily_free_ai_router.py`;
- nevertheless, the scoring guard evaluated **10** items in the same cycle;
- the reason was architectural: queue prechecks are executed by `intily_scoring_runtime_guard.py` outside the legacy publisher loop, while the router only changed `publisher.MAX_ATTEMPTS_PER_RUN`;
- therefore the advertised router cap did not actually cap the queue-precheck AI calls.

This caused unnecessary provider consumption and increased exposure to free-tier quota exhaustion. Run #1396 recorded 10 Gemini evaluations before publication and the historical 24h monitor showed 61.05% publish-attempt failure rate and 60.0% no-publish rate.

## Fix

`AI_MAX_EVALUATIONS_PER_RUN` in `scripts/intily_scoring_runtime_guard.py` is now `2`, matching the free router. The guard is the authoritative limiter for both queue prechecks and candidate evaluations.

The existing router remains free-first:

1. Gemini
2. Groq
3. OpenRouter `openrouter/free`
4. OpenAI

No editorial prompt was changed. No live Cloudflare Worker was changed. No queue/state reset was performed.

## Verification

Before the fix, run #1396 was verified directly from GitHub Actions logs:

- `AI_EVALUATION_CAP 2`
- `AI_EVALUATION_START` 1 through 10
- `AI_EVALUATION_LIMIT_REACHED 10`
- Telegram delivery succeeded as `TELEGRAM_SENT 1382`.

The repository test suite at that run passed 62 tests, including the free-router tests. A test was updated so the scoring guard contract explicitly expects a cap of 2.

## Acceptance criteria for the next production observation

A fresh production run must show:

- `AI_EVALUATION_CAP 2`;
- no more than 2 `AI_EVALUATION_START` events per cycle;
- no provider outage loop after a quota failure;
- queued eligible item can still reach Telegram;
- `BUSINESS_RESULT PUBLISHED telegram_delivery_ok` when a publication is made;
- queue remains durable;
- no change to the live Cloudflare Worker.

This change is not considered production-proven until a fresh post-change GitHub Actions run is observed and its logs confirm the above behavior.
