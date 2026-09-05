# INTILY Full Production Audit — 2026-09-05

## Result

**GREEN — production is operating on the restored architecture and the repository split is complete on the active/default branches.**

The intended production contract is:

`Cloudflare JavaScript Cron scheduler → GitHub Actions workflow_dispatch → Python publisher → Telegram`

The deliberate infrastructure change is that the Intily code now lives in the public `knyavik-stack/intily-news` repository instead of the former mixed `knyavik-stack/synapsemax` repository.

## 1. GitHub repository separation

### Canonical Intily repository

- Repository: `knyavik-stack/intily-news`
- Visibility: public
- Default branch: `main`
- Canonical production code:
  - `cloudflare/intily-ai-news.worker.js`
  - `cloudflare/wrangler.jsonc`
  - `scripts/intily_ai_news.py`
  - `.github/workflows/intily-ai-news.yml`
  - `data/intily-ai-news-state.json`

### SynapseMax

The active `main` branch was audited before and after separation.

The following Intily-owned artifacts were removed atomically from SynapseMax `main`:

- Intily GitHub Actions workflow
- Intily publisher script
- Intily state file
- Intily operations/publication/handoff/status documents
- historical Intily Worker/Python backup artifacts

Cleanup commit: `7478752170dd5635357958ad51c7271ed537e334`.

The temporary branch `chore/remove-intily-from-synapsemax` was deleted after the cleanup landed in `main`.

Historical recovery branches and the baseline tag were intentionally preserved. They are archival recovery material, not active production sources and must not be treated as the canonical SynapseMax runtime.

## 2. Cloudflare production runtime

Worker: `intily-ai-news`

Active production version:

- version number: `87`
- version ID: `b20948d7-c11c-4495-a9ca-421c9fb58dcc`
- handlers: `fetch`, `scheduled`
- deployment: 100%
- compatibility date: `2026-09-01`
- usage model: `standard`

The active source is JavaScript (`worker.js`). It is not the Python-native Worker experiment.

The production schedule is exactly one Cron Trigger:

`* * * * *`

The Worker itself applies the historical approximately 1/3 dispatch gate and sends a `workflow_dispatch` request to:

`knyavik-stack/intily-news/.github/workflows/intily-ai-news.yml`

The old Workers Builds trigger created during the failed Python migration was deleted. The active production deployment is API-created from the restored JavaScript source; no Python build root or Python build command is part of the production runtime.

## 3. GitHub Actions

There is exactly one active Intily workflow: `Intily AI News Publisher`.

Trigger model:

- `workflow_dispatch` only
- no GitHub schedule
- concurrency group: `intily-ai-news-production`
- `cancel-in-progress: false`
- publisher timeout: 5 minutes
- Python process timeout: 240 seconds

The workflow uses GitHub Secrets for:

- `TELEGRAM_BOT_TOKEN`
- `GROQ_API_KEY`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`

No secret values are stored in the repository.

## 4. Runtime verification

Recent Intily workflow runs after restoration were successful, including the automatic dispatch path. The latest audited run completed with `success`.

The publisher state was observed in a healthy state with:

- `last_status = OK`
- empty `last_error`
- a live publication queue

This confirms that the restored scheduler is not merely deployed: it is dispatching the canonical publisher successfully.

## 5. Security audit

The Intily repository is public.

GitHub repository security state:

- Secret Scanning: enabled
- Secret Scanning Push Protection: enabled
- Dependabot security updates: disabled

A `.gitignore` has now been added to prevent accidental inclusion of `.env` files, local environments, Python caches and logs.

The public state JSON was checked for secret-like token material; no secret token pattern was found in the audited state.

Production rules:

- never commit `.env` files
- never print secret environment variables
- never place API tokens in JSON/state files
- never include secrets in debug/error output
- runtime credentials remain in GitHub/Cloudflare secret stores

## 6. Architecture boundary

### INTILY owns

- Telegram news collection
- scoring/ranking
- deduplication
- queueing
- AI editing
- Telegram publication
- publication state
- Cloudflare scheduler
- Intily operational documentation

### SynapseMax owns

- SynapseMax website/application code
- SynapseMax-specific workflows and documentation
- SynapseMax assets and product development

There is no active Intily production dependency on SynapseMax `main`.

## 7. Intentional historical artifacts

The repositories retain historical commits/branches/tags for rollback and forensic traceability. Historical presence is not an active dependency.

In particular, the old SynapseMax baseline tag and recovery branch must be treated as immutable recovery evidence, not as sources for future Intily development.

## 8. Remaining non-blocking note

Cloudflare's historical deployment list contains old experimental versions from the failed Python-native migration. They are not serving production traffic. The active deployment is the restored JavaScript scheduler.

No further production migration is authorized by this audit. The system should remain on this architecture until a separately tested, measurable replacement is proven without changing the live path.
