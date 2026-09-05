# INTILY — Telegram AI News Automation

INTILY is the dedicated Telegram AI news publication subsystem.

## Current production status

**GREEN — restored to the proven 2026-09-05 08:00 MSK architecture.**

Production is intentionally simple:

1. Cloudflare `intily-ai-news` runs a **JavaScript** minute scheduler.
2. The scheduler dispatches GitHub Actions roughly once every three minutes via a 1/3 gate.
3. GitHub Actions runs the **Python** publisher.
4. The publisher discovers, ranks, deduplicates, queues and publishes to Telegram.
5. Publisher state is persisted to `data/intily-ai-news-state.json`.

The public repository is the only deliberate structural change from the pre-cutover production setup. The Cloudflare source is version-controlled under `cloudflare/`.

## Canonical documentation

- `docs/INTILY_RUNTIME_RESTORATION_2026-09-05.md` — restoration record and architecture contract.
- `docs/PROJECT_STATUS_2026-09-06.md` — current verified state.
- `docs/INTILY_PUBLICATION_SETTINGS.md` — publication controls.
- `docs/INTILY_OPERATIONS.md` — operational reference.

## Security

This repository is public. Secret values must never be committed or printed to logs. Runtime secrets are stored in GitHub/Cloudflare secret stores.


## Production KPI and monitoring

Every publisher run records a bounded production history in `data/intily-ai-news-state.json` and renders the KPI dashboard in the GitHub Actions **Summary**.

For an on-demand current dashboard, open **Actions → Intily Production Monitor → Run workflow**.

Operator controls are explicitly marked in `scripts/intily_ai_news.py` and `scripts/intily_monitor.py`. Monitoring controls do not disable publication.
