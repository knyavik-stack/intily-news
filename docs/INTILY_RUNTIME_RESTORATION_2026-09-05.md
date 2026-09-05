# Intily runtime restoration — 2026-09-05 08:00 MSK baseline

## Canonical restored architecture

The production architecture is restored to the proven pre-cutover design:

```text
Cloudflare Worker (JavaScript scheduler)
  -> GitHub Actions workflow_dispatch
  -> Python publisher (`scripts/intily_ai_news.py`)
  -> Telegram @intily
  -> state persisted back to GitHub
```

### Cloudflare baseline

- Worker: `intily-ai-news`
- Baseline version: **54**
- Version ID: `8d9de9eb-7e28-4880-a46f-881fce654f8f`
- Runtime: **JavaScript module** (`worker.js`)
- Compatibility date: `2026-09-01`
- Cron: `* * * * *` (UTC)
- Scheduler gate: one out of three minute ticks dispatches GitHub, preserving the approximately 3-minute publication cadence.
- The Worker does not run the Python publisher itself.

The source in `cloudflare/intily-ai-news.worker.js` is recovered from Cloudflare version 54. The only production-neutral change is the GitHub repository target: the scheduler now dispatches the same workflow in the dedicated `knyavik-stack/intily-news` repository.

## GitHub baseline

The publisher and workflow are restored from the original 08:00 MSK cutoff commit in `knyavik-stack/synapsemax`:

- source commit: `334f4ae9561864b9c5a32470b4d6de3e5c1b25fa`
- commit time: `2026-09-05T04:59:25Z`
- publisher: `scripts/intily_ai_news.py`
- workflow: `.github/workflows/intily-ai-news.yml`

The live state file is intentionally **not rewound** to the historical snapshot. It remains the current production state so that restoration of code does not create duplicate Telegram publications from stories already processed after the cutoff. This is operational state, not architecture drift.

## Security

The repository is public. No secret values are stored in source, workflow, state, or documentation. Runtime credentials remain GitHub/Cloudflare secrets. Secret scanning was checked and no alerts were returned at restoration time.

## Explicit non-goals

- No Python runtime in Cloudflare.
- No Cloudflare-native RSS ingestion.
- No Browser Run dependency in production.
- No GitHub Actions `schedule`.
- No second production scheduler.
- No Workers Builds trigger for this Worker.

## Verification requirement

A restoration is accepted only after: Cloudflare active deployment is JavaScript v54-equivalent, cron is `* * * * *`, GitHub `workflow_dispatch` succeeds in `intily-news`, the publisher run reports `OK`, and Telegram publication/state persistence are observed.
