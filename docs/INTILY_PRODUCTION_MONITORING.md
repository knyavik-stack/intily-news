# Intily Production KPI & Monitoring

## Purpose

This layer separates the **technical GitHub Actions result** from the **business result of the publisher**. A green workflow means the job completed technically; `business_result` says whether a Telegram publication actually happened.

## Where to view

### 1. Every production run
GitHub → `intily-news` → **Actions** → **Intily AI News Publisher** → open a run → **Summary**.

The Summary contains the current cycle and rolling KPI dashboard.

### 2. On-demand dashboard
GitHub → **Actions** → **Intily Production Monitor** → **Run workflow**.

This reads the durable state without publishing anything. The dashboard is Markdown-first and exposes executive KPIs, discovery/admission funnel, RSS/provider health, NO_PUBLISH classification, admission blocks, source yield and recent-cycle telemetry. The monitor never publishes.

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
- publication rate and frequency;
- candidate volume;
- queue velocity and size;
- NO_PUBLISH cycles and reasons;
- item publication failures and failure rate;
- admission volume and rate;
- RSS query/direct-feed health;
- source-level yield;
- actual provider usage and failovers;
- recent cycle telemetry.

Each cycle stores search execution, candidates, queue before/after, admission telemetry, publication attempts, failures and provider state. No provider secret/token is stored.

## Alert policy

The monitor deliberately distinguishes **incident RED** from **diagnostic WARN**. This prevents a healthy production system from being marked failed merely because a KPI is below an unvalidated editorial target.

### Hard RED

- `ALERT_NO_PUBLISH_RUNS = 10`: 10 consecutive cycles without publication.
- `ALERT_PUBLISH_FAILURES_24H = 5` **and** `ALERT_PUBLISH_FAILURE_RATE = 20%`: at least 5 publication/item failures in 24h and at least 20% of attempts failed, with a minimum 10-attempt sample.
- `ALERT_RSS_ERROR_RATE = 25%`: at least 25% of Google News RSS queries fail, with a minimum 10-query sample.

These thresholds are incident guards, not claims about the ideal editorial cadence. They are intentionally conservative until a longer empirical SLO baseline exists and must be reviewed annually with the project threshold rationale.

### Diagnostic WARN

- publication failures ≥3 and ≥10% of attempts;
- admission rate below 10% once at least 50 telemetry-covered candidates exist;
- candidates present but zero admissions in the latest cycle;
- direct RSS feed errors.

Admission rate is **not** a hard failure criterion. A low rate can be correct when candidates are duplicates of already-published stories or blocked by semantic history. The dashboard exposes the admission-block distribution so the operator can distinguish genuine news scarcity from downstream rejection.

## Why Monitor run #4 failed

On 2026-09-06, `Intily Production Monitor` run **#4** failed only in `Check production alerts`. The dashboard itself completed successfully. The old monitor treated `8` PUBLISH_FAILED events in 24h as an automatic RED because its threshold was simply `>=3`, and it also treated admission rate below `10%` as RED. The observed sample was `68` publication attempts, `8` failures (`11.76%`) and `99` telemetry-covered candidates with `6` admissions (`6.06%`).

Those values are important diagnostics, but they do not by themselves prove an incident. The monitor was therefore corrected to keep them visible as WARN while reserving workflow failure for sustained, high-rate incidents. This fixes the false-positive monitor failure without hiding the underlying KPI degradation.

## NO_PUBLISH classification

`NO_PUBLISH` is operationally classified. In particular, `admission_blocked_<reason>` means fresh candidates existed but zero candidates entered the durable queue. This distinguishes a genuine lack of qualifying discovery from an admission-memory/dedup bottleneck.

## Queue starvation protection

The exact RSS-item memory (`known`) is a short anti-hot-loop guard with a **90-minute TTL**. It is not an editorial blacklist. Long-lived duplicate protection remains the `published` + semantic `stories` layer.

## Production telemetry expansion — 2026-09-06

The production cycle now records proof-level telemetry for the complete discovery → admission → editorial AI → Telegram path. This is additive observability; it does not alter the one-publication-per-cycle contract.

### Priority-A KPI schema

Each `run_history` record may contain:

- `admission`: published-key, known-recent, already-queued, story-queue, story-history and added counts, plus admission rate and dominant block.
- `rss`: queries attempted/OK/errors, raw items, score/quality filtering, discovery story dedup, candidate count and candidate yield.
- `provider`: actual provider used, provider attempts, failovers, failures, blocked providers and missing-key skips. No API secrets are stored.
- cycle duration, publication attempts, item failures, business result/reason, queue before/after.

The monitor aggregates these values over 24h, 7d and the stored sample. Publication frequency is calculated from the actual timestamp span, not from an assumed scheduler cadence.

## Source resilience / Priority-B foundation — 2026-09-06

Google News remains the broad aggregator layer, but production now also reads a small curated set of direct publisher feeds: TechCrunch AI, VentureBeat AI, The Verge AI, OpenAI News, Google DeepMind, Hugging Face, Ars Technica and Habr News. The code records per-source yield and direct-feed errors for future source intelligence.

This is deliberately a small resilience layer, not an uncontrolled feed explosion. Priority-B source intelligence will use the recorded source-yield data to decide which sources deserve more query/feed budget.

## Telemetry migration hardening — 2026-09-06

Admission-rate and similar derived metrics are migration-aware: historical cycles that predate the expanded telemetry schema are not counted in the denominator for the new admission SLO. This prevents a false RED caused by mixing old and new schemas.

## Verification

After changing monitor logic, validate both modes:

```text
python3 scripts/intily_monitor.py
python3 scripts/intily_monitor.py --check
```

The first command must render a complete Markdown dashboard. The second must return exit code `0` unless a hard incident threshold is genuinely breached.
