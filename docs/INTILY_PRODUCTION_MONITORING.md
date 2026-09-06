# Intily Production KPI & Monitoring

## Purpose

This layer separates the **technical GitHub Actions result** from the **business result of the publisher**. A green workflow means the job completed technically; `business_result` says whether a Telegram publication actually happened.

## Where to view

### 1. Every production run
GitHub → `intily-news` → **Actions** → **Intily AI News Publisher** → open a run → **Summary**.

The Summary contains the current cycle, rolling KPI dashboard and the **current-run search intelligence**. The latter explains which Google News queries and direct feeds actually supplied fresh material in this launch.

### 2. On-demand dashboard
GitHub → **Actions** → **Intily Production Monitor** → **Run workflow**.

This reads the durable state without publishing anything. The dashboard is Markdown-first and exposes executive KPIs, discovery/admission funnel, RSS/provider health, NO_PUBLISH classification, admission blocks, source yield and recent-cycle telemetry. The monitor never publishes.

### 3. Raw history
`data/intily-ai-news-state.json` → `run_history`. The history is bounded to the latest 200 production cycles.

Search intelligence history is kept separately in `data/intily-query-intelligence.json`, bounded to the latest 100 launches. It contains only query/source counters and derived percentages; no article bodies, API keys or provider secrets.

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

## Dashboard correctness hardening — 2026-09-06

The first corrected dashboard exposed a second presentation defect: it mixed cycle-level candidates with RSS-only telemetry and divided all publications by newly admitted items, which produced a misleading `700%` publication ratio. This was a **dashboard calculation defect**, not a publisher defect.

Commit `de456bd518e6f1f5f8e66564509b24b4661a9f59` corrected the funnel to use RSS candidate telemetry for the RSS yield stage and reports publication rate against production cycles, explicitly noting that publication can consume previously queued items.

Real Actions run **#6** (`34024533836`) completed SUCCESS and verified the corrected output: `RSS raw=2506`, `RSS candidates=367` (`14.6%`), `admitted=9` (`2.9%` of telemetry-covered candidates), `published=63` (`31.5%` of cycles). No invalid >100% publication ratio remains.

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

## Search intelligence — 2026-09-06

The publisher workflow now captures the **current launch's actual search stream** without making any extra RSS calls. The publisher's existing `RSS_QUERY`, `RSS_DIRECT`, `INGEST_SUMMARY` and `QUEUE_ADMISSION` telemetry is parsed after the publisher finishes.

The current-run block is shown in the same GitHub Actions Summary as the publisher dashboard, in Russian, and contains:

- сколько свежих материалов пришло из Google News;
- сколько пришло из прямых RSS;
- сколько материалов отсечено score-фильтром;
- сколько отсечено quality/AI relevance;
- сколько схлопнуто как одна история;
- сколько осталось кандидатов;
- сколько реально добавлено в очередь;
- таблицу поисковых запросов с регионом, текстом запроса, количеством свежих материалов и долей общего поискового потока;
- таблицу прямых источников и их свежий yield;
- понятное объяснение, является ли проблема discovery или admission.

История поискового потока сохраняется отдельно в `data/intily-query-intelligence.json` (100 последних запусков). Это сделано специально, чтобы не раздувать основной `run_history` и не менять publisher только ради аналитики.

### Важное ограничение текущей версии

На этом этапе запросы получают достоверный **raw-yield**, но не получают искусственно приписанную им admission-конверсию. Один и тот же материал может прийти из нескольких запросов, а publisher дедуплицирует уже общий пул. Поэтому распределять `added` между запросами без явной provenance-маркировки было бы ложной точностью.

Следующий эволюционный шаг — лёгкая provenance-маркировка `query_id` на этапе ingestion. Она позволит считать `запрос → raw → score → quality → story-dedup → admission` без повторных RSS-запросов. Реализовывать её имеет смысл после накопления нескольких запусков raw-yield, чтобы сначала увидеть фактическую картину и не усложнять production преждевременно.

## Telemetry migration hardening — 2026-09-06

Admission-rate и подобные derived metrics migration-aware: исторические циклы, предшествующие расширенной telemetry-схеме, не считаются в знаменателе нового admission SLO. Это предотвращает ложный RED из-за смешения старой и новой схем.

## Verification

Static validation compiled the exact committed monitor source successfully. Regression fixtures reproduced the Monitor #4 sample and returned `MONITOR GREEN`; a deliberate 5/10 publication-failure fixture returned `MONITOR RED` as intended.

The search-intelligence parser is intentionally side-effect-light: it reads only the current publisher stdout, performs no network calls, bounds history at 100 launches and stores no secrets.

GitHub Actions job summaries are the correct UI for this design: GitHub documents that `GITHUB_STEP_SUMMARY` accepts GitHub-flavored Markdown and is displayed on the workflow run summary page. citeturn1search0turn1search1

Real GitHub Actions verification previously completed successfully:

- Monitor run **#5** (`34024493076`) — corrected incident-vs-warning policy: SUCCESS.
- Monitor run **#6** (`34024533836`) — corrected funnel calculations: SUCCESS.

The next production verification must confirm the new search-intelligence step and its persistence on a real publisher launch before this enhancement is considered fully closed.
