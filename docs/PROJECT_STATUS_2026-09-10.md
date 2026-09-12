# INTILY Project Status — 2026-09-12

## Canonical current status

**🟠 PRODUCTION SCHEDULER INCIDENT — publisher code is healthy, but no Cloudflare-dispatched production run has been observed since 2026-09-11 12:32 UTC.** The user reported no Telegram posts for about two hours; repository evidence is stronger: the latest verified production run is #1062 at 12:32 UTC on 2026-09-11, so the scheduler gap is substantially longer than two hours.

The publisher itself remains production-capable: #1062 completed successfully, ran 53/53 preflight tests, used Gemini successfully, published to `@intily`, and persisted state/analytics. The current failure is therefore at the scheduler/dispatch layer, not in the Python publisher path.

Production contract:

`Cloudflare intily-ai-news scheduler → GitHub Actions workflow_dispatch → Python production entrypoint → Telegram @intily → durable GitHub state`

Telegram posts contain **editorial content only**. Queue statistics, queue-next information and operational diagnostics remain disabled (`SHOW_QUEUE_DIAGNOSTICS = False`).

## Scheduler incident — 2026-09-12

Verified facts:

- GitHub production workflow is `workflow_dispatch` only.
- Latest verified production run: #1062, started 2026-09-11 12:32 UTC and completed successfully.
- No newer production run has been observed in the available GitHub Actions evidence.
- Therefore the Python publisher cannot currently be blamed for the missing posts: there is no fresh workflow execution to inspect.
- The versioned worker in GitHub previously used a probabilistic 1/3 gate on a per-minute cron. That design did not provide a bounded maximum dispatch gap.
- The deployed Cloudflare Worker itself cannot be inspected or redeployed from the currently available ChatGPT integrations; no Cloudflare plugin/connection capable of Worker deployment is available in this session.

### Durable scheduler fix prepared

The versioned worker `cloudflare/intily-ai-news.worker.js` has been replaced with a minimal scheduler-only implementation:

- cron is now `*/5 * * * *`;
- the probabilistic 1/3 gate is removed;
- every scheduled tick dispatches `intily-ai-news.yml` on `main`;
- missing `GITHUB_DISPATCH_TOKEN` is an explicit error;
- non-2xx GitHub dispatch responses are explicit errors;
- `/health` reports scheduler version `6.0` and the configured cron;
- obsolete duplicate publishing code, stale `@intilyshop` destination logic and obsolete Cloudflare AI publishing path were removed from the worker because production publishing is performed by GitHub Actions/Python.

Commit: `29ced61d5ae78f1d699c98b64cf9abb0a016ff59`.

**Important:** this fixes the canonical worker source in GitHub but does not itself redeploy the already-running Cloudflare Worker. Cloudflare deployment is the remaining external action required to restore live scheduling.

## CI incident — Regression Gate #17–#21 — CLOSED

The exact historical #17–#19 failure chain is not falsely attributed to Pillow without their logs. What is factually established is:

- production run #1018 installed **Pillow 12.3.0**;
- production then passed all 50 regression tests;
- the regression suite did not need Pillow for its fixture contract;
- Regression Gate previously ran on production state/analytics pushes, creating unnecessary CI coupling/churn.

Durable fix:

- deterministic stdlib-only image fixtures;
- no Pillow installation in Regression Gate;
- `paths` filters for `scripts/**` and the regression workflow;
- production `data/**` writes do not start regression CI.

## Media gate — no-orphan-image policy

Telegram `sendPhoto` captions are limited to 1024 characters after entity parsing. The runtime counts visible characters rather than UTF-8 bytes.

Current production media policy:

- **≤1024 visible caption characters:** image + complete editorial text in one photo message;
- **>1024 visible characters:** no photo call; complete editorial text sent exactly once;
- image retrieval/validation/delivery failure: complete text fallback;
- editorial text is never truncated and an orphan image is never intentionally published.

Regression Gate #35 passed **53/53** on the corrected policy. Fresh live proof of both branches remains open because the scheduler stopped dispatching before those observations could be collected.

## Provider gate

Failover order remains:

1. Gemini — primary;
2. Groq `openai/gpt-oss-20b` — fallback;
3. OpenAI — fallback if key/quota is available.

Current tests prove bounded Groq quota handling. Fresh live fallback evidence remains open.

## Current gates

### 🟢 GREEN

- Python production publisher end-to-end in verified runs;
- Gemini primary;
- Telegram text delivery;
- durable state;
- queue/dedup/final-score invariant;
- canonical user editorial prompt;
- image retrieval/validation and real Telegram photo delivery in previous production runs;
- provider retry hardening implemented and regression-tested;
- Regression Gate #35 **53/53 green**;
- production run #1062 successful;
- Pillow 12.3.0 proven compatible with production test/runtime path;
- no-orphan media policy implemented and regression-tested;
- deterministic five-minute scheduler source prepared and committed.

### 🟠 RED/OPEN — live scheduling

- Cloudflare Worker must be redeployed from commit `29ced61d5ae78f1d699c98b64cf9abb0a016ff59`;
- after deployment, verify at least one `workflow_dispatch` run immediately and several consecutive cycles;
- verify Telegram publication resumes;
- then collect fresh live evidence for short-caption photo and long-caption text-only branches;
- then collect fresh live Groq fallback evidence.

### 🔴 Known blocker

**Live scheduler deployment is the current critical blocker.** No known critical blocker exists in the Python publication engine itself.

## Acceptance rule

**fact → root cause → implementation → tests → real production run → telemetry inspection → documentation.**

Commit/CI success alone is never production proof.
