# INTILY Production Status — 2026-09-03

## Current architecture

`Cloudflare Cron → intily-ai-news Worker → GitHub workflow_dispatch → scripts/intily_ai_news.py → Telegram`

Cloudflare is the scheduler; GitHub Actions is the publisher execution environment. The workflow remains `workflow_dispatch` only. GitHub documents that workflow dispatch requires the workflow to accept that event, and the REST endpoint supports dispatch by workflow filename/ref.

## Production policy

- Search: every 30 minutes, or immediately at queue size 0–1.
- Publication: one story per cycle, minimum 3 minutes between posts.
- Importance: 0–100 deterministic model; only >=60 enters queue/publication.
- Queue: max 20; RU minimum 50% when enough qualifying RU stories exist.
- Humor: target 90% on suitable non-serious stories; serious topics suppress humor.
- Candidate queue reset: performed without deleting published-story history.

## Verification

Live full collector test: 216 raw items → 51 qualifying candidates; 31 WORLD / 20 RUSSIA. This is sufficient to satisfy the 50% RU queue quota at the 20-item cap.

Manual GitHub publisher run after the first policy commit completed successfully.

Cloudflare scheduler was changed from the observed `*/2` to the required `*/3 * * * *`. Active deployment is version 44 after this scheduler-only update; all four existing bindings are retained.

## Backups

`docs/backups/2026-09-03/intily_ai_news.py.prechange` — publisher before policy migration.
`docs/backups/2026-09-03/intily-ai-news.worker.v43.prechange.js` — exact Cloudflare Worker source before scheduler migration.
`docs/backups/2026-09-03/intily-ai-news-state.prechange.json` — durable state before queue reset.
Cloudflare version 43 remains the infrastructure rollback point.


## Temporary queue diagnostics — 2026-09-03

Added a temporary Telegram footer for production observation. It reports the queue state after the just-published item is removed: total queue size, RU count, WORLD count, and the importance percentage of the next queued story. The feature is controlled by `SHOW_QUEUE_DIAGNOSTICS` in `scripts/intily_ai_news.py` and is currently `True`.

No Cloudflare Worker source or schedule was changed for this feature. The current GitHub publisher was backed up before modification at `docs/backups/2026-09-03/intily_ai_news.py.pre-queue-diagnostics-2026-09-03`.

## Temporary RU weighting experiment — 2026-09-03

- Russian-news queue target changed from 50% to **60%** when enough qualifying RU candidates exist. At the 20-item queue cap this reserves 12 RU slots.
- Russian candidates receive a **random +1 to +5 percentage-point importance bonus** at ingestion. The bonus is stored in `russia_weight_bonus` and is applied once; existing queued items are not re-rolled on every cycle.
- The bonus is capped by the global 0–100 importance ceiling.
- This is an explicit temporary analytical experiment and must remain documented until the Boss requests removal.
- Temporary queue footer remains enabled via `SHOW_QUEUE_DIAGNOSTICS = True`.
