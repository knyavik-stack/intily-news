# INTILY Project Status — 2026-09-06

## Production status: GREEN

The Intily publication pipeline has been restored to the proven **08:00 MSK architecture**. The important correction is now verified from Cloudflare's historical Worker version itself: the Cloudflare scheduler at the cutoff was **JavaScript**, not Python. Python belongs to the GitHub Actions publisher.

## Canonical production architecture

```text
Cloudflare `intily-ai-news` (JavaScript scheduler)
        │  * * * * *
        │  ~1/3 dispatch gate
        ▼
GitHub Actions `Intily AI News Publisher`
        │
        ▼
Python `scripts/intily_ai_news.py`
        │
        ├── discovery / ranking / dedup / queue
        ├── editorial QA / formatting
        └── Telegram publication
        │
        ▼
`data/intily-ai-news-state.json`
```

This is the architecture that is running now. There is **no Python runtime in Cloudflare production**.

## Cloudflare — verified production

- Worker: `intily-ai-news`
- Historical cutoff version: **v54**
- Historical version ID: `8d9de9eb-7e28-4880-a46f-881fce654f8f`
- Restored production version: **v87**
- Restored version ID: `b20948d7-c11c-4495-a9ca-421c9fb58dcc`
- Runtime: `application/javascript+module`
- `main_module`: `worker.js`
- Compatibility date: `2026-09-01`
- Cron: `* * * * *` UTC
- Active traffic: 100% → v87
- v87 bindings inherit from v54; secret values were never exposed during restoration.
- Workers Builds trigger: removed; it is not part of production.

The v87 source is the recovered v54 JavaScript scheduler with exactly one intentional runtime change: the GitHub dispatch target now points to the dedicated public repository `knyavik-stack/intily-news`. The scheduling behavior and publication architecture are otherwise preserved.

## GitHub — verified production

Canonical repository: `knyavik-stack/intily-news`

- Visibility: **public**
- Main branch restored with the 08:00 publisher/workflow baseline.
- Restoration commit: `dd012ae4dbd90eece3c9ac90f23fd3a96fc12817`
- Original 08:00 source commit: `334f4ae9561864b9c5a32470b4d6de3e5c1b25fa`
- Workflow remains `workflow_dispatch` only; there is no GitHub Actions scheduler.
- Standard `ubuntu-latest` runner is used. Public repositories using standard GitHub-hosted runners are free and unlimited according to current GitHub documentation.

## Live verification

1. Manual smoke test: run `33996052882` → **success**.
2. Automatic Cloudflare dispatch: run `33996109387` → **success**.
3. Next automatic Cloudflare dispatch: run `33996156465` → **success**.
4. Persisted state health after the automatic run: `last_status=OK`, `last_error=''`, queue remains populated, no secret-like credential pattern detected.

## State policy

The production state file was deliberately **not rewound** to the historical 08:00 snapshot. The code/runtime architecture was restored; operational state continues from the live state so stories already published after the cutoff are not re-published.

## Security

The repository is public, so source and workflow are intentionally visible. Secret values remain outside Git. Secret Scanning and Push Protection are enabled. No secret value was copied into source, JSON state, documentation, or Cloudflare source during this restoration.

## Explicitly removed from production path

- Cloudflare Python-native RSS runtime.
- Browser Run dependency.
- Cloudflare-native Google RSS collection.
- GitHub Actions `schedule`.
- Workers Builds auto-deploy trigger.
- Second production scheduler.

## Next safe step

Do not redesign the runtime now. Keep the restored architecture stable and observe several automatic publication cycles. Any future optimization must be implemented as a separate, reversible canary with source parity and rollback verified before promotion.
