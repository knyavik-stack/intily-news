# INTILY Project Status — 2026-09-09

## Canonical current status

**🟡 PRODUCTION VERIFICATION MODE — scoring/queue fix deployed, live new-search verification pending.**

This document supersedes the 2026-09-08 status for current state. The production contract remains: deterministic base 0–70 → AI audience +3…+30 → final 0–100 → queue/publication ordered by final score descending. Geography is not part of the mathematical score.

## Verified defect and correction

The previous queue implementation still had three paths that could make the user-visible queue diverge from the agreed final-score contract:

1. finalized and pending `pre_ai` items were sorted in one numeric field (`importance`), so a pending base score could outrank an already-finalized lower score;
2. the legacy `rebalance_queue()` enforced a regional quota before final sorting and could discard a higher-scoring story in favor of lower-scoring RU stories;
3. the publication priority was guarded, but the legacy regional candidate selection and rebalance remained separate ordering authorities.

The runtime guard was hardened so there is now one ordering authority:

`AI final score → queue ranking → publication priority`.

Changes committed in `scripts/intily_scoring_runtime_guard.py`:

- final items always outrank pending `pre_ai` items;
- among finalized items, `final_score` is the primary key and timestamp is only a tie-breaker;
- the legacy regional quota rebalance is bypassed in production in favor of a pure score-capacity rebalance (`MAX_QUEUE`);
- pre-AI items cannot outrank finalized items during publication selection;
- legacy pre-AI queue wording is removed from generated posts;
- the main publisher's existing queue diagnostic now operates on the guarded pure-score rebalance, so `В очереди` uses the same ranking authority as publication;
- score footer remains complete and non-truncating.

## Regression coverage

The runtime guard test suite now additionally verifies that a finalized 56-point item outranks a pending 69-point pre-AI item. The existing tests continue to cover:

- no legacy +10 pre-AI audience placeholder;
- AI 10/10 contribution reaches +30;
- final score is primary ordering key;
- all score components are printed;
- over-limit editorial text is rejected instead of truncated.

The workflow currently runs the scoring, audience, image, Google News and runtime-guard regression suites before production execution.

## Live evidence already available

Production run #764 (`34265206024`) was successful and executed 32/32 regression tests. It pre-evaluated 7 queued items with AI audience scores and published a 64-point item. Queue audit reported `final_below_threshold=0`. However, that run skipped discovery (`SEARCH_SKIPPED`), so it did not prove the specific scenario of new discovery candidates entering an already populated queue and changing its final-score order.

The same run exposed an unrelated audience-calibration quality issue: one terrorism-related story received an audience score of 8. This is not part of the queue-ordering defect and remains a separate editorial-model calibration item.

## Current code commits

- `438982e9d3386f2df8eda9ba4c6666c258d5d197` — scoring runtime guard: final-score ordering, pure score rebalance, truthful queue handling.
- `fb1cda0016d53bb63bc6f0e4457e284a789857be` — regression test: finalized items ahead of pending queue items.

## Remaining acceptance test

The next production run that actually performs discovery must demonstrate, in one real cycle:

1. new candidates are discovered;
2. each admitted candidate receives AI audience evaluation before queue admission whenever the provider is available;
3. final scores are persisted on the candidates;
4. the durable queue is reordered by final score, not geography or editorial heuristics;
5. `В очереди` reports the same top item/score that the publisher will select;
6. the highest finalized score is published;
7. no finalized item below 55 remains in the durable queue;
8. score footer values exactly match the persisted score components;
9. no editorial text is truncated.

Until that real new-search scenario passes, project status remains **YELLOW**. A green test suite alone is not sufficient.
