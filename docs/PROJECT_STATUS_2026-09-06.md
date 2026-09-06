# INTILY Project Status — 2026-09-06

## Production status: GREEN

Production remains on the restored 2026-09-05 08:00 MSK architecture. This change adds observability only; it does not change the scheduler, publisher cadence, discovery, editorial policy, or Telegram delivery path.

## Observability closure

Implemented:

- explicit business result per production cycle: `PUBLISHED`, `NO_PUBLISH`, `PUBLISH_FAILED`;
- reason code for every non-publication;
- bounded `run_history` (200 cycles) persisted in the existing durable state;
- rolling 24h / 7d KPI calculations;
- candidate volume, queue size, publication count, attempts and item failures;
- GitHub Actions run Summary dashboard on every publisher run;
- on-demand `Intily Production Monitor` workflow;
- RED checks for prolonged no-publish and publication failures;
- operator controls and disable instructions documented directly beside code.

## Operator access

Primary: GitHub → Actions → `Intily AI News Publisher` → any run → **Summary**.

On-demand: GitHub → Actions → `Intily Production Monitor` → **Run workflow**.

Raw durable history: `data/intily-ai-news-state.json` → `run_history`.

## Important distinction

GitHub Actions `SUCCESS` means the technical workflow completed successfully. The KPI `business_result` says whether the production objective was achieved. Therefore a green Action with `NO_PUBLISH` is a normal, observable business outcome rather than an ambiguous green box.

## Remaining maturity work

No architecture change is required. Remaining maturity is empirical: accumulate a meaningful production sample and evaluate publication rate, queue pressure, candidate yield, provider failures and no-publish streaks against agreed SLOs.


## Live verification — monitoring closure

Verified after deployment commit `d19f3fb39f718d3199942b193dd489932a94e2c1`: publisher run **#27** completed SUCCESS and produced a real Telegram publication. The runtime emitted `BUSINESS_RESULT PUBLISHED`, `publish_attempts=1`, `item_failures=0`, `queue_after=13`, and persisted state successfully.

The same run generated the KPI dashboard in the GitHub Actions Summary. The on-demand `Intily Production Monitor` was then run against the persisted state and completed GREEN, showing 24h/7d/stored history with 1 run, 1 publication, 100% publication rate and 0 item failures.

This confirms the complete observability path: **publisher → durable KPI history → Actions Summary → on-demand monitor → alert check**.

## Production correction — 2026-09-06

A 10-hour production analysis proved that the RSS layer had not run out of AI news: production had continued to discover candidates and successfully publish. The bottleneck was downstream candidate admission. The exact admission path showed a 6-hour `known` memory acting as a hard barrier for repeated Google News RSS items.

Correction deployed: `known` is now a 90-minute technical anti-hot-loop memory; published and semantic story memory remain the durable duplicate protections. This allows a previously seen but never published story to be reconsidered without opening the door to republishing already published events.

At the same time, Priority-A telemetry was expanded to expose admission rejection reasons, RSS health, actual AI provider usage/failover, queue velocity, publication frequency, PUBLISH_FAILED statistics and precise NO_PUBLISH classification.

### Current engineering status

- Production architecture unchanged: Cloudflare scheduler → GitHub Actions → Python publisher → Telegram.
- The fix is behaviorally narrow and is covered by syntax/static validation before production smoke.
- Empirical tuning remains pending until a larger post-fix sample accumulates.


## Priority-B start — source resilience

The discovery layer now has two independent paths: Google News RSS query clusters plus curated direct publisher RSS feeds. Per-source yield and direct-feed error telemetry is persisted for subsequent source-intelligence analysis. This directly addresses the observed failure mode where Google News returned many candidates but the majority were already present in publication memory.


## Production verification — 2026-09-06

Direct-RSS production smoke on commit `9aad362ebf93014a516acee95e47b241a810f90b` completed successfully. Observed in one cycle: 31/31 Google News queries OK; 8 direct feeds attempted, 7 OK, 1 HTTP 429; 134 raw items; 20 candidates; 2 admitted; 1 published to Telegram; Gemini used successfully with zero failover; queue ended at 1. This proves the new source layer is live and capable of recovering publishable items beyond the Google-only candidate set.

A later monitoring hardening commit `b98bf1ec8f223d3e81d02219296fd57e77a4e54d` made derived KPI rates migration-aware.

Current known limitation: some direct publisher feeds returned zero fresh items in the smoke window, and VentureBeat returned HTTP 429. These are now visible as source-level health signals rather than silent gaps.
