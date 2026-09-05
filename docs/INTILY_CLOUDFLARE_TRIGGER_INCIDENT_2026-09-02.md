# Intily Cloudflare Scheduler Incident — 2026-09-02 / recovery updated 2026-09-03

## Root cause confirmed

The canonical production architecture is:

`Cloudflare Worker intily-ai-news → GitHub Actions workflow_dispatch → scripts/intily_ai_news.py → Telegram @intily`

The GitHub workflow intentionally has only `workflow_dispatch`; Cloudflare is therefore responsible for initiating every production cycle.

During the failed recovery, the active Cloudflare Worker had been replaced operationally with direct RSS/AI/Telegram publishing logic. Its source contained no GitHub dispatch call, while the repository workflow had no GitHub-native schedule. Consequently automatic GitHub runs stopped even though manual runs continued to succeed.

## Production correction

On 2026-09-03 the full deployed Worker source was preserved and patched only at the scheduler boundary:

- `scheduled()` now calls authenticated GitHub workflow dispatch;
- target: `knyavik-stack/synapsemax`;
- workflow: `.github/workflows/intily-ai-news.yml`;
- ref: `main`;
- Cloudflare secret `GITHUB_DISPATCH_TOKEN` remains inherited;
- canonical cadence restored to `*/11 * * * *` in both the Worker guard and Cloudflare schedule;
- `AI`, `STATE`, `TELEGRAM_BOT_TOKEN` and `GITHUB_DISPATCH_TOKEN` bindings were retained.

## Verified facts

- Manual workflow run `33718306259` completed `success` on 2026-09-03.
- The workflow file is `workflow_dispatch` only, confirming Cloudflare dispatch is required for automation.
- The active Worker now contains the GitHub dispatch scheduler path and Cloudflare schedule `*/11 * * * *`.

## Acceptance criterion

Recovery is GREEN only after a new GitHub Actions run appears automatically after a Cloudflare cron boundary and completes through the publisher pipeline. Until then the dispatch restoration is deployed but runtime observation remains pending.
