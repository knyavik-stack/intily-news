# INTILY Project Status — 2026-09-09

## Canonical current status

**🟡 PRODUCTION VERIFICATION MODE — scoring/queue ordering fix and provider/pre-AI hardening deployed; fresh live verification pending.**

This document is the canonical current status. The production contract remains: deterministic base 0–70 → AI audience +3…+30 → final 0–100 → queue/publication ordered by final score descending. Geography is not part of the mathematical score.

## Verified defect and correction — queue ordering

The previous queue implementation still had three paths that could make the user-visible queue diverge from the agreed final-score contract:

1. finalized and pending `pre_ai` items were sorted in one numeric field (`importance`), so a pending base score could outrank an already-finalized lower score;
2. the legacy `rebalance_queue()` enforced a regional quota before final sorting and could discard a higher-scoring story in favor of lower-scoring RU stories;
3. the publication priority was guarded, but the legacy regional candidate selection and rebalance remained separate ordering authorities.

The runtime guard was hardened so there is now one ordering authority:

`AI final score → queue ranking → publication priority`.

Changes in `scripts/intily_scoring_runtime_guard.py`:

- final items always outrank pending `pre_ai` items;
- among finalized items, `final_score` is the primary key and timestamp is only a tie-breaker;
- the legacy regional quota rebalance is bypassed in production in favor of a pure score-capacity rebalance (`MAX_QUEUE`);
- pre-AI items cannot outrank finalized items during publication selection;
- legacy pre-AI queue wording is removed from generated posts;
- the queue diagnostic uses the same ranking authority as publication;
- score footer remains complete and non-truncating.

## Newly verified production defect — provider timeout and pre-AI gate drift

A subsequent production log exposed a separate, critical runtime problem. The run ingested 496 items but ended with exit code 124 because Gemini quota exhaustion triggered repeated 429 retries while Groq was already circuit-open and OpenAI blocked. The exact sequence was `GEMINI_RETRY 429 5`, `10`, `20`, followed by repeated editorial failures until the five-minute workflow budget expired.

The same run exposed a scoring-contract drift in the legacy collector:

- legacy `IMPORTANCE_THRESHOLD` was 60 although canonical pre-AI gate is 40;
- legacy collection still added a random Russian-region score bonus before filtering.

Observed ingestion telemetry: raw 496, score-filtered 449, quality-filtered 4, story-dedup 16, candidates 27. The score buckets contained 416 items below 40, demonstrating that the production input stream is substantially broader than the legacy 60-point admission path.

Added `scripts/intily_production_entrypoint.py` as the production entrypoint before the scoring guard. It forces the canonical 40-point pre-AI gate, strips the legacy regional bonus before canonical scoring, filters true base scores below 40, and changes Gemini quota handling to a single request followed by a six-hour provider circuit on quota-exhaustion 429. A dedicated regression test covers the one-shot 429 behavior.

Incident documentation: `docs/PRODUCTION_INCIDENT_2026-09-09_AI_PROVIDER_TIMEOUT.md`.

## Regression coverage

The workflow now runs the scoring, audience, image, Google News, runtime-guard and production-entrypoint regression suites before production execution.

Current regression coverage includes:

- no legacy +10 pre-AI audience placeholder;
- AI 10/10 contribution reaches +30;
- final score is primary ordering key;
- finalized items outrank pending pre-AI items;
- all score components are printed;
- over-limit editorial text is rejected instead of truncated;
- canonical pre-AI threshold is 40;
- Gemini 429 path performs exactly one request instead of an unbounded retry loop.

## Live evidence

Production run #764 (`34265206024`) successfully executed 32/32 previous regression tests, pre-evaluated 7 queued items and published a 64-point item. However, discovery was skipped in that run, so it did not prove the new-search reorder scenario.

The later production log supplied for the 2026-09-09 incident demonstrated the new-search ingestion path but failed on provider exhaustion and therefore cannot be used as a successful acceptance run.

## Current commits

- `438982e9d3386f2df8eda9ba4c6666c258d5d197` — final-score queue ordering guard.
- `fb1cda0016d53bb63bc6f0e4457e284a789857be` — finalized-vs-pending ordering regression test.
- `6fbc091907051e1961787100d085c858b802702c` — hardened production entrypoint: canonical pre-AI gate and Gemini fail-fast.
- `ff0f25e80cc10b41584965d6fde077512eb567a7` — production-entrypoint regression test.
- `18200a2d8019530a93a070524a645f5ed4a2c4ed` — workflow uses hardened entrypoint and test.
- `187669758afa55628b7a0f72084c69ad382a046b` — incident documentation.

## Remaining acceptance test

The next real production cycle must demonstrate all of the following in one run:

1. fresh discovery completes;
2. the canonical pre-AI gate is 40, without geographic/random score bonus;
3. candidates above 40 are AI-evaluated when a provider is available;
4. provider failure is fail-fast and does not consume the workflow budget;
5. final scores are persisted;
6. the durable queue is reordered by final score, not geography or editorial heuristics;
7. `В очереди` reports the same top item/score that publication will select;
8. the highest finalized score is published;
9. no finalized item below 55 remains in the durable queue;
10. score footer values exactly match persisted score components;
11. no editorial text is truncated.

Until this live acceptance cycle passes, status remains **YELLOW**.
