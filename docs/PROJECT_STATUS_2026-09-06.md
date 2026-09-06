# INTILY Project Status — 2026-09-06

## Production status: 🟡 GREEN TECHNICALLY / YELLOW EDITORIAL SUPPLY

Production architecture is working. The current concern is not scheduler failure or empty RSS discovery, but insufficient fresh unique stories after duplicate/history checks.

## Production architecture

```text
Cloudflare intily-ai-news
  → GitHub Actions workflow_dispatch
  → scripts/intily_ai_news.py
  → Telegram @intily
  → data/intily-ai-news-state.json
```

GitHub publisher has no own cron.

## Observability

Implemented:

- explicit business result per production cycle: `PUBLISHED`, `NO_PUBLISH`, `PUBLISH_FAILED`;
- reason code for every non-publication;
- bounded `run_history` (200 cycles) persisted in durable state;
- rolling 24h / 7d KPI calculations;
- candidate volume, queue size, publication count, attempts and item failures;
- GitHub Actions Summary dashboard;
- on-demand `Intily Production Monitor`;
- RED checks for prolonged no-publish and publication failures;
- provider usage/failover telemetry;
- RSS/query/direct-feed health telemetry;
- admission rejection telemetry;
- queue velocity and publication frequency.

## Critical terminology

Numbers in the pipeline are different:

```text
RSS raw
  ↓
score / freshness / AI relevance / story dedup
  ↓
CANDIDATES
  ↓
published / known / queue / semantic history checks
  ↓
NEW QUEUE ADMISSIONS
  ↓
durable queue
  ↓
AI editorial QA
  ↓
Telegram publication
```

Therefore `19 candidates` and `0 new admissions` are not contradictory.

## Live diagnosis — 2026-09-06 09:34 UTC

The verified production cycle produced:

- 154 RSS raw items;
- 31/31 Google News queries OK;
- 8 direct feeds attempted: 7 OK, 1 HTTP 429;
- 124 items removed by score;
- 26 candidates after quality/relevance/story dedup;
- 0 new queue admissions;
- 23 candidates rejected because the exact item key was already published;
- 3 candidates rejected by semantic story history;
- 0 publications in that cycle;
- technical health `OK`.

### Root cause

The discovery layer is **not empty**. It found 26 candidates.

The immediate bottleneck is that the candidate pool is dominated by stories the channel already knows/published.

## Important telemetry bug found and corrected

`scripts/intily_ai_news.py` previously calculated `dominant_block` while including `candidate_count` among the possible causes.

That was incorrect because `candidate_count` is the size of the input, not a rejection reason. With 26 candidates it could incorrectly report:

```text
admission_blocked_candidate_count
```

while the real cause was, for example:

```text
published_key = 23
story_history = 3
```

The production hotfix now selects `dominant_block` only from actual rejection causes:

- `published_key`;
- `known_recent`;
- `already_queued`;
- `story_queue`;
- `story_history`.

The change is applied by a one-time migration step in the production workflow and committed back to main.

## Why 19 candidates existed 12–15 hours earlier

The verified 2026-09-02 production cycle received 169 RSS items and produced 19 candidates. One was published and the queue then became empty.

This does not mean there should always be 19 new publishable stories later. Google News can return the same recent stories repeatedly. Once Intily has published those stories, they correctly stop at the admission layer.

The current problem is therefore **fresh unique supply**, not a broken candidate scorer.

## Current source health

Google News queries are currently returning material and have shown 0 query errors in the verified cycle.

Direct RSS sources are a resilience layer, but several currently return no fresh items in the active window and VentureBeat has returned HTTP 429. These are now visible in telemetry.

## Next engineering priority — Query + Source Intelligence

Do not blindly add dozens of RSS feeds.

Instrument every query/source separately:

- raw items;
- fresh items;
- candidates;
- already-published rejects;
- semantic rejects;
- new admissions;
- publication yield;
- error rate;
- WORLD/RUSSIA contribution.

Then rank query/source clusters by actual production value.

Add fresh source-focused queries using Google News time operators such as `when:6h` and `when:1h` where appropriate, while preserving the existing editorial gates. Google News RSS supports search operators including `when:` and `site:`; these are useful for building focused fresh-source streams. citeturn1search0turn0search8

## Future roadmap

1. Query + Source Intelligence.
2. Full editorial funnel analytics.
3. Topic yield and source yield.
4. Historical trend analysis.
5. Adaptive query allocation.
6. Adaptive scoring after empirical data exists.
7. Adaptive publication timing after Telegram performance data exists.
8. Anomaly detection.
9. Weekly executive report in Russian.
10. Telegram content-performance analytics only when a reliable data source is available.

Do not fabricate Telegram views/reactions/CTR until reliable measurements exist.

## Operator rule

After every material change:

**inspect → root cause → fix → verify → document**.

A successful GitHub Action is not by itself proof of editorial correctness.
