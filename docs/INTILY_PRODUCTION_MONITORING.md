# Intily Production KPI & Monitoring

## Purpose

This layer separates the **technical GitHub Actions result** from the **business result of the publisher**. A green workflow means the job completed technically; `business_result` says whether a Telegram publication actually happened.

## Where to view

### 1. Every production run
GitHub → `intily-news` → **Actions** → **Intily AI News Publisher** → open a run → **Summary**.

The Summary contains the current cycle and rolling KPI dashboard.

### 2. On-demand dashboard
GitHub → **Actions** → **Intily Production Monitor** → **Run workflow**.

This reads the durable state without publishing anything. With the monitor check enabled, configured RED thresholds cause the monitor workflow to fail, making an operational alert visible in GitHub.

### 3. Raw history
`data/intily-ai-news-state.json` → `run_history`. The history is bounded to the latest 200 production cycles.

## Business statuses

- `PUBLISHED` — Telegram accepted the publication.
- `NO_PUBLISH` — cycle completed normally but no post was sent; `business_reason` explains why.
- `PUBLISH_FAILED` — publication was attempted and failed.

Technical `SUCCESS` and business `PUBLISHED` are intentionally separate.

## KPI

The dashboard reports for 24h, 7d and the stored sample:

- production runs;
- publications;
- no-publish cycles;
- publication rate;
- average candidates;
- average queue size after the cycle;
- item publication failures;
- consecutive no-publish cycles.

Each cycle also stores search execution, candidates, queue before/after, publication attempts, failures and provider circuit state. No provider secret/token is stored.

## Alerts

`ALERT_NO_PUBLISH_RUNS = 10` — RED when 10 consecutive cycles produce no publication.

`ALERT_ITEM_FAILURES_24H = 3` — RED when 3 or more item publication failures occur within 24h.

Set either threshold to `0` to disable that alert. The controls are marked directly in `scripts/intily_monitor.py`.

These are initial operational thresholds, not claims about the ideal editorial cadence. After a meaningful production sample is collected, they should be tuned from observed KPI/SLO data.

## How to disable KPI collection

In `scripts/intily_ai_news.py`, under `Production KPI / monitoring`, change `KPI_MONITORING_ENABLED = True` to `False`. The code comment beside the flag explicitly states that this **does not disable publication**; it only stops recording the bounded KPI history.

## Safety

Monitoring is read-only with respect to Telegram and providers. It reads the state file and GitHub Actions metadata only. It never prints secret values.


## Verified production smoke test

On 2026-09-05 UTC the production publisher smoke test completed successfully with `PUBLISHED`, one Telegram delivery, zero item publication failures and durable state persistence. The subsequent on-demand monitor read the persisted history and returned `GREEN`.
