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
