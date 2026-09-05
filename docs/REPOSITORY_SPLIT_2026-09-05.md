# INTILY repository split — 2026-09-05

## Decision

INTILY news publication is now maintained as a dedicated repository: `knyavik-stack/intily-news`. SynapseMax remains the website/application repository and must not contain the Intily publisher.

## Baseline

The split starts from the production rollback baseline corresponding to **2026-09-05 08:00 MSK (05:00 UTC)**. The baseline commit is `334f4ae9561864b9c5a32470b4d6de3e5c1b25fa`.

## Migrated scope

Migrated from SynapseMax:

- publisher engine `scripts/intily_ai_news.py`;
- GitHub Actions workflow `.github/workflows/intily-ai-news.yml`;
- durable publisher state `data/intily-ai-news-state.json`;
- Intily operations/publication settings/handoff/status documentation;
- Cloudflare scheduler incident documentation;
- historical Intily backups from 2026-09-03 and 2026-09-04.

## Safety sequencing

1. New repository is created and populated.
2. New repository contents are verified.
3. Cloudflare dispatch/build wiring is switched to the new repository.
4. New repository runtime is smoke-tested.
5. Only after the new path is proven, Intily files are deleted from SynapseMax.

This order prevents an otherwise healthy production publisher from being disconnected during the repository split.

## Secrets

The workflow references repository secrets `TELEGRAM_BOT_TOKEN`, `GROQ_API_KEY`, `OPENAI_API_KEY`, and `GEMINI_API_KEY`. Secret values are not copied because GitHub's secrets API intentionally does not reveal them. The active repository must have these secrets available before GitHub Actions is switched to `intily-news`.

## Future work

The next architectural task is to eliminate dependence on GitHub-hosted Actions minute quotas while keeping this repository as the canonical source of the Intily publication code.
