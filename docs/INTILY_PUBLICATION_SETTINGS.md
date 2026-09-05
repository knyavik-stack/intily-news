# INTILY Publication Settings

**Single control point:** `scripts/intily_ai_news.py` → `PUBLICATION SETTINGS`.

| Setting | Value | Meaning |
|---|---:|---|
| Search interval | 30 min | Planned news discovery cadence |
| Publication interval | 3 min | Minimum gap between Telegram posts |
| Importance threshold | 60/100 | Minimum candidate importance |
| Max queue | 20 | Maximum qualifying stories in memory |
| RU minimum share | 50% | Minimum RU share when enough RU candidates exist |
| Joke rate | 90% | Target for suitable non-serious posts |
| Urgent queue threshold | 1 | Search immediately at 0–1 queued stories |
| Temporary queue diagnostics | ON | Adds queue size, RU/WORLD counts, and next-item importance to every published post; remove by setting `SHOW_QUEUE_DIAGNOSTICS = False` |

## Where to operate

- **Code/settings:** `scripts/intily_ai_news.py`
- **Automation trigger:** Cloudflare Worker `intily-ai-news` → Cron `*/3 * * * *`
- **Publisher workflow:** `.github/workflows/intily-ai-news.yml`
- **Durable candidate state:** `data/intily-ai-news-state.json`
- **Rollback snapshot:** `docs/backups/2026-09-03/`


## Validation snapshot — 2026-09-03

A live full-collector test returned 216 raw items, 51 qualifying candidates after the 60/100 threshold, with 31 WORLD and 20 RUSSIA candidates before queue capping. The queue rebalance therefore has enough RU inventory to build a 20-item queue with the required 10/10 minimum split.

A production test also exposed and corrected a concrete Cyrillic-data defect in the previous implementation: Russian AI relevance terms and Russian search queries had been stored as mojibake, causing Russian discovery to return zero results and Russian relevance to fail. The current implementation uses native UTF-8 Cyrillic terms and queries.

## Temporary publication diagnostics

For temporary production analysis, every Telegram post currently receives a final diagnostic line:

`📊 В очереди: X новостей, RU — Y, WORLD — Z. Следующая в очереди имеет вес P%.`

The values describe the queue **after the published story is removed**, using the same queue filtering/rebalancing rules as production. `P` is the `importance` value (0–100) of the next queued story after rebalancing. If the queue is empty, the footer reports that the next story is absent.

This is deliberately feature-flagged. To remove it later, change `SHOW_QUEUE_DIAGNOSTICS = True` to `False` in the publication settings; no queue logic needs to be changed.


## Temporary RU experiment (2026-09-03)

- `RUSSIA_MIN_SHARE = 0.60`
- `RUSSIA_MIN_QUEUE_SLOTS = 12` for a 20-item queue
- Russian candidates receive random `russia_weight_bonus` from **+1 to +5** importance points at ingestion.
- Bonus is applied once per newly collected candidate and persisted with the candidate; it is not re-randomized during queue maintenance.
- Purpose: temporary measurement of how stronger RU representation and a small stochastic weight advantage affect queue composition and publication order.
- Remove only after the analytical period is complete.


## Production KPI / monitoring controls

- KPI collection: `scripts/intily_ai_news.py` → `KPI_MONITORING_ENABLED`.
- KPI history size: `KPI_HISTORY_LIMIT`.
- Monitoring alert threshold: `scripts/intily_monitor.py` → `ALERT_NO_PUBLISH_RUNS`.
- 24h publication-failure alert: `ALERT_ITEM_FAILURES_24H`.
- Disabling KPI collection does **not** disable publication; it only stops bounded KPI history recording.

## How to view statistics

1. Open `intily-news` on GitHub.
2. Open **Actions → Intily AI News Publisher** and open a completed run.
3. Open the run **Summary** to see the KPI dashboard.
4. For an on-demand dashboard, open **Actions → Intily Production Monitor → Run workflow**.
5. Raw durable history is in `data/intily-ai-news-state.json` under `run_history`.

### Status meanings

- `PUBLISHED` — Telegram delivery succeeded.
- `NO_PUBLISH` — the cycle completed normally but no post was sent; `business_reason` explains why.
- `PUBLISH_FAILED` — publication was attempted and failed.
- GitHub `SUCCESS` is the **technical** workflow result, not a publication guarantee.
