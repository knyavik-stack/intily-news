# INTILY Production Changelog — 2026-09-15 — Provider Recovery Retirement Fix

## Incident

Production cycles were still publishing nothing after the free-first router and AI evaluation cap fixes.

Run #1407 completed successfully as a GitHub Action, but published **0** items. The router reported all four live providers as blocked:

- GEMINI
- GROQ
- OPENROUTER
- OPENAI

The workflow preflight nevertheless logged `AI_PROVIDER_RECOVERY_SKIP provider_available`.

## Root cause

`intily_provider_recovery.py` treated `GITHUB_TOKEN` as a configured `GITHUB_MODELS` AI provider.

GitHub Models is retired for this project, while `GITHUB_TOKEN` is still intentionally present for state/analytics persistence. Therefore the recovery helper could incorrectly conclude that an AI provider was available and refuse to clear an actual all-live-provider deadlock.

This was a recovery-logic bug, not a Telegram or RSS failure.

## Fix

The recovery helper is now aligned exactly with the providers used by `intily_free_ai_router.py`:

`GEMINI -> GROQ -> OPENROUTER -> OPENAI`

`GITHUB_MODELS` was removed from the configured-provider and environment-provider lists. The GitHub token therefore cannot masquerade as an available AI provider.

A regression test now verifies that a present `GITHUB_TOKEN` does not prevent all-live-provider recovery.

## Safety

- No live Cloudflare Worker was modified.
- No Telegram configuration was modified.
- Queue/state is not reset by this change.
- Recovery still clears circuits only when every configured live router provider is blocked.
- Provider order and editorial prompt remain unchanged.

## Verification

The change is committed to `main` together with the regression test. The next production cycle must show either:

1. `AI_PROVIDER_RECOVERY_ALL_BLOCKED` followed by a successful provider call and Telegram delivery; or
2. a precise new runtime failure identifying the next blocking condition.

A GitHub Actions green status alone is not accepted as production proof.
