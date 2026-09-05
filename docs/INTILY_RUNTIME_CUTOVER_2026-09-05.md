# INTILY Runtime Cutover — 2026-09-05

## Status

`knyavik-stack/intily-news` is the canonical Intily publication repository. The SynapseMax cleanup branch is prepared but is not merged until production runtime cutover is proven.

Production remains on the proven Cloudflare Worker v54 + GitHub Actions fallback. This was intentional: the GitHub Actions smoke test in `intily-news` is blocked by the exhausted GitHub-hosted runner quota.

## Secrets verified

The target repository contains these required Actions secrets:

- `GEMINI_API_KEY`
- `GROQ_API_KEY`
- `OPENAI_API_KEY`
- `TELEGRAM_BOT_TOKEN`

Secret values are not stored in documentation.

## Native runtime canary

Cloudflare Worker `intily-ai-news` native Python Worker version 84 was tested as a reversible canary.

- Version ID: `30f2d545-5735-468e-8f4e-6911052ea1bf`
- Version number: 84
- Python Workers runtime: present
- Browser binding: present
- AI binding: present
- KV binding: present
- Telegram binding: present

The native Worker executed successfully enough to write its health state to KV. This proves the native scheduled runtime is technically executable.

The canary was **not accepted for production** because it initialized the publisher state with an empty state object. The current live publisher state must be migrated explicitly before activation. The canary was rolled back immediately.

## Current production baseline

- Active Worker version: 54
- Active version ID: `8d9de9eb-7e28-4880-a46f-881fce654f8f`
- Restoration deployment: `c354677c-d431-47af-beb8-bbdd20102839`
- Cron: `* * * * *`

The proven fallback is restored.

## Critical state rule

Cloudflare Worker deployment rollback does not roll back KV storage. The native runtime and the historical scheduler also use different logical state contracts. Future activation must therefore migrate the live publisher state deliberately and verify it before switching traffic.

The latest live publisher state was captured from `synapsemax/main`. It is about 100 KB and contains publication history, semantic story memory, queue data, provider state and timing information. It must not be reset or reconstructed from scratch.

## Production activation gates

Before native activation:

1. Migrate the latest live publisher state into the native publisher-state contract.
2. Bring the native runtime up to the current `intily-news` publication logic.
3. Prove Google News/RSS ingestion in Cloudflare, including the historical 503 issue.
4. Prove AI fallback and Telegram publication end-to-end.
5. Run a controlled publication test and verify state persistence.
6. Switch the production Cron only after all checks are green.
7. After several successful cycles, merge the SynapseMax cleanup branch.

Rollback target: Worker version 54 (`8d9de9eb-7e28-4880-a46f-881fce654f8f`).
