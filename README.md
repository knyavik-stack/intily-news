# INTILY News

Dedicated repository for the INTILY Telegram AI-news publication system.

## Scope

This repository contains only the news-publication subsystem: discovery, RSS ingestion, scoring and editorial filtering, duplicate protection, queue management, Telegram formatting/publication, GitHub Actions fallback runtime, durable publisher state, operational documentation, and historical Intily backups.

The SynapseMax website/application is intentionally kept in the separate `synapsemax` repository.

## Production architecture (baseline 2026-09-05 08:00 MSK)

- Cloudflare Worker `intily-ai-news` runs every minute.
- The Worker applies the 1/3 execution gate and dispatches the GitHub Actions workflow when selected.
- GitHub Actions runs `scripts/intily_ai_news.py`.
- Publisher state is persisted in `data/intily-ai-news-state.json`.
- Telegram destination: `@intily`.

## Important

The repository was split from `knyavik-stack/synapsemax` after the production rollback to the 2026-09-05 08:00 MSK baseline. The separation is intentionally staged: the new repository must be verified and Cloudflare dispatch/build wiring switched before the Intily files are removed from SynapseMax.

## Documentation

- `docs/INTILY_OPERATIONS.md` — operational runbook.
- `docs/INTILY_PUBLICATION_SETTINGS.md` — publication policy and control points.
- `docs/USER_HANDOFF.md` — handoff for future chats/operators.
- `docs/NEW_CHAT_START_PROMPT.md` — project continuity prompt.
- `docs/PROJECT_STATUS_2026-09-04.md` — latest pre-rollback project status retained as historical reference.
- `docs/INTILY_CLOUDFLARE_TRIGGER_INCIDENT_2026-09-02.md` — scheduler incident history.

## Secrets

GitHub Actions secrets are intentionally not copied into source control. GitHub does not expose secret values through its API; they must be recreated or moved through the appropriate GitHub secret-management mechanism before this repository becomes the active Actions target.
