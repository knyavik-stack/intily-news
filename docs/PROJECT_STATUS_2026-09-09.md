# INTILY Project Status — 2026-09-09

## Canonical current status

**🟡 PRODUCTION VERIFICATION MODE — scoring/queue ordering and provider/pre-AI hardening deployed; Gemini rate-limit hardening deployed; live AI publication verification pending.**

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

Added `scripts/intily_production_entrypoint.py` as the production entrypoint before the scoring guard. It forces the canonical 40-point pre-AI gate, strips the legacy regional bonus before canonical scoring, filters true base scores below 40, and provides GitHub Models as an emergency AI fallback.

## Gemini rate-limit hardening — deployed

The production Gemini adapter is now deliberately conservative:

- minimum **5 seconds between Gemini requests** (12 RPM ceiling at most, leaving margin below a 15-RPM-style limit);
- bounded exponential retry for **transient** 429 responses: 2s → 4s → 8s → 16s;
- explicit `quota_exceeded` / daily-quota responses are **not retried** and immediately open the provider circuit;
- prompts are bounded to `12,000` characters, preserving the beginning and end and marking the cut with `[CONTEXT_TRUNCATED]`;
- the GitHub Models fallback receives the same bounded prompt;
- the existing six-hour provider circuit prevents a failed provider from consuming the production budget repeatedly.

This is intentionally stricter than merely assuming that every 429 means “15 RPM exceeded”. Google's current documentation states that Gemini limits are model/tier/project dependent and can apply across RPM, input TPM and RPD; it distinguishes transient `rate_limit_exceeded` from `quota_exceeded`, recommending exponential backoff for transient limits and waiting for quota reset for exhausted daily quota. citeturn0search0turn0search1turn0search2

## Live evidence after first hardening

Production run #792 (`34316757631`) is the first post-fix live discovery run:

- 35/35 regression tests passed;
- discovery executed;
- 499 raw items → 26 candidates;
- `CANONICAL_PRE_AI_FILTER 26 -> 26 threshold 40.0` confirmed the canonical gate;
- Gemini 429 failed immediately with no retry loop;
- Gemini circuit opened for six hours;
- the workflow completed normally rather than timing out;
- 8 new candidates entered the durable queue.

However, all original AI vendors were unavailable at that moment, so the run published 0. This confirms the timeout and gate fixes, but not yet the full fallback/publication path. GitHub Models fallback was deployed immediately afterward.

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
- Gemini quota 429 performs exactly one request;
- transient Gemini 429 uses bounded exponential backoff;
- Gemini prompts are bounded;
- GitHub Models fallback uses the documented OpenAI-compatible endpoint.

## Current commits

- `438982e9d3386f2df8eda9ba4c6666c258d5d197` — final-score queue ordering guard.
- `fb1cda0016d53bb63bc6f0e4457e284a789857be` — finalized-vs-pending ordering regression test.
- `6fbc091907051e1961787100d085c858b802702c` — hardened production entrypoint: canonical pre-AI gate and Gemini fail-fast.
- `bdd599bc87991bdafaf5b5413e2adf6f6fa69c7a` — GitHub Models emergency AI fallback.
- `c1424cd1bdde405a7d4fbc9f184048b532e37fdc` — Gemini 5-second throttle, transient-429 backoff and prompt bound.
- `480624a32cd9815dea9c36f9b0a60d11a138b471` — regression coverage for quota/transient 429 and prompt bound.

## Remaining acceptance test

The next real production cycle must demonstrate all of the following in one run:

1. fresh discovery completes;
2. canonical pre-AI gate is 40, without geographic/random score bonus;
3. at least one candidate receives a real AI audience score through a healthy vendor or GitHub Models fallback;
4. provider failure is fail-fast and does not consume the workflow budget;
5. final scores are persisted;
6. durable queue ordered by final score, not geography or editorial heuristics;
7. `В очереди` matches the actual top item/score that publication will select;
8. highest finalized score is published;
9. no finalized item below 55 remains in durable queue;
10. footer values exactly match persisted components;
11. no editorial text is truncated.

Until this live acceptance cycle passes, status remains **YELLOW**.
