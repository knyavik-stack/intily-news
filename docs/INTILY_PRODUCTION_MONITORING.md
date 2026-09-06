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

## Production telemetry expansion — 2026-09-06

The production cycle now records proof-level telemetry for the complete discovery → admission → editorial AI → Telegram path. This is additive observability; it does not alter the one-publication-per-cycle contract.

### Priority-A KPI schema

Each `run_history` record may contain:

- `admission`: published-key, known-recent, already-queued, story-queue, story-history and added counts, plus admission rate and dominant block.
- `rss`: queries attempted/OK/errors, raw items, score/quality filtering, discovery story dedup, candidate count and candidate yield.
- `provider`: actual provider used, provider attempts, failovers, failures, blocked providers and missing-key skips. No API secrets are stored.
- cycle duration, publication attempts, item failures, business result/reason, queue before/after.

The monitor aggregates these values over 24h, 7d and the stored sample. Publication frequency is calculated from the actual timestamp span, not from an assumed scheduler cadence.

### NO_PUBLISH classification

`NO_PUBLISH` is now operationally classified. In particular, `admission_blocked_<reason>` means fresh candidates existed but zero candidates entered the durable queue. This distinguishes a genuine lack of qualifying discovery from an admission-memory/dedup bottleneck.

### Queue starvation protection

The exact RSS-item memory (`known`) is a short anti-hot-loop guard with a **90-minute TTL**. It is not an editorial blacklist. Long-lived duplicate protection remains the `published` + semantic `stories` layer. The monitor raises RED when the latest cycle has candidates but zero admissions and when sustained admission/failure thresholds are breached.

### Operator dashboard

Run **GitHub → Actions → Intily Production Monitor → Run workflow** for a read-only dashboard. Every publisher run also writes the KPI dashboard to the workflow **Summary** page. The monitor never calls Telegram, RSS or AI providers.

### Configuration / disabling

- KPI collection: `scripts/intily_ai_news.py` → `KPI_MONITORING_ENABLED`. Disabling it stops KPI history only; publication continues.
- Exact-item memory TTL: same file → `KNOWN_LOOKBACK_SECONDS`.
- Monitor alerts: `scripts/intily_monitor.py` → `ALERT_*` constants. Set an individual threshold to `0` to disable that alert.

### Verification requirement

The new telemetry is intentionally designed to accumulate evidence for Priority B/C optimization. Do not tune SLO thresholds from a tiny sample; use the rolling dashboard after a meaningful production window.


## Source resilience / Priority-B foundation — 2026-09-06

Google News remains the broad aggregator layer, but production now also reads a small curated set of direct publisher feeds: TechCrunch AI, VentureBeat AI, The Verge AI, OpenAI News, Google DeepMind, Hugging Face, Ars Technica and Habr News. The code records per-source yield and direct-feed errors for future source intelligence.

The source catalog was chosen from currently available publisher RSS endpoints. TechCrunch publishes RSS feeds and provides RSS terms requiring attribution/link preservation; Ars Technica documents its RSS feeds; VentureBeat documents its RSS endpoints; Habr documents RSS availability. citeturn0search2turn0search6turn0search1turn0search0turn3search0

This is deliberately a small resilience layer, not an uncontrolled feed explosion. Priority-B source intelligence will use the recorded source-yield data to decide which sources deserve more query/feed budget.


## Telemetry migration hardening — 2026-09-06

Admission-rate and similar derived metrics are migration-aware: historical cycles that predate the expanded telemetry schema are not counted in the denominator for the new admission SLO. This prevents a false RED caused by mixing old and new schemas.
