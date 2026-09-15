# INTILY Production Changelog — 2026-09-15 — Provider Circuit Recovery

## Incident

Production runs #1365 and #1366 completed successfully at the GitHub Actions level but published **0** items. The latest run #1366 was not a scheduler failure: the workflow executed the publisher and ended with `NO_PUBLISH no_eligible_item` because the AI evaluation layer had no available provider.

Verified #1366 evidence:

- Gemini: `GEMINI_CIRCUIT_OPEN`;
- Groq: HTTP 429 with `tokens per day` / `rate limit reached` for `openai/gpt-oss-20b`;
- OpenAI: `OPENAI_CIRCUIT_OPEN`;
- publisher then emitted `PUBLICATION_HALTED provider_runtime_unavailable`;
- durable queue remained intact at **11** items;
- queue invariant remained `invariant_ok:true`;
- no Telegram delivery attempt occurred because editorial AI evaluation could not complete.

## Root cause

The persisted provider circuit-breaker state could deadlock the publisher across production cycles when **all configured providers were simultaneously marked unavailable**. The existing recovery utility was operator-triggered only; normal production runs did not automatically reopen the circuits when the entire provider set was blocked.

This is distinct from the earlier scheduler incident: the GitHub production workflow was running normally in #1365/#1366.

## Fix

### Automatic all-blocked recovery

`scripts/intily_provider_recovery.py` now supports `--all-blocked` mode.

Behavior:

1. Determine configured providers from the production environment.
2. If at least one configured provider is not blocked, do nothing.
3. If every configured provider is blocked, clear **only provider circuit state** (`disabled_until`, `reason`).
4. Queue, published history, story memory and editorial state are untouched.
5. The normal publisher then performs real provider requests and re-establishes circuit state based on the actual provider responses.

### Production workflow

`.github/workflows/intily-ai-news.yml` now runs the recovery preflight immediately before the publisher.

The recovery is therefore automatic and bounded: it does not reset healthy provider circuits and cannot reset the publication queue.

## Regression evidence

- Regression Gate #41: **success** after the recovery implementation.
- Regression Gate #42: **success** after adding tests for the all-blocked recovery behavior.
- Existing provider-recovery tests remain green.

## Production acceptance still required

A fresh Cloudflare-dispatched production cycle must prove:

`AI_PROVIDER_RECOVERY_ALL_BLOCKED → provider request succeeds → AI evaluation → Telegram delivery`

or, if all providers are genuinely unavailable, the logs must prove that the system retries the next cycle without permanent circuit deadlock.

Acceptance rule remains:

**fact → root cause → implementation → tests → real production run → telemetry inspection → documentation.**
