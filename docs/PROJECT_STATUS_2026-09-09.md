# INTILY Project Status — 2026-09-09

## Canonical current status

**🟡 PRODUCTION VERIFICATION MODE — scoring/queue ordering and provider/pre-AI hardening deployed; workflow-budget hardening deployed; live acceptance partially verified by run #847; full acceptance still pending log-level proof of every invariant.**

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

## Production incident — AI evaluation exceeded workflow budget

The failed Action was run #834 (`34346240698`), commit `5d7993c03ac6e66e452c3831bc2fe8c0fa9fa398`. The publish job failed in the production engine step after the regression suite completed 38/38 OK; analytics and state persistence still executed.

The production engine performed a fresh search and produced 43 candidates. Gemini was healthy, but the runtime evaluated candidates serially at the conservative 5-second request spacing. The run reached 42 AI evaluations and was killed by the explicit `timeout 240s` wrapper with `exit code 124` before queue/publication could complete.

This exposed a second-order design defect: provider rate limiting was bounded, but the number of AI evaluations was not bounded. With 43 candidates, a 5-second inter-request guard alone can consume more than the workflow's total budget after discovery, state loading and persistence overhead.

## Workflow-budget hardening — deployed

The production runtime now has a shared AI-evaluation deadline of **180 seconds**, intentionally below the workflow's 240-second production command timeout. The deadline covers both pending queue items and fresh candidates.

Before starting each new model evaluation, the guard checks the deadline. When the budget is exhausted, it stops starting new AI calls, leaves remaining candidates as `pre_ai`, sorts the resulting queue using the canonical final-score authority, and returns control to the normal publisher so durable state can still be saved. This prevents `timeout 240s` / exit 124 from killing the entire cycle.

Additional hardening:

- Gemini request timeout reduced to 20 seconds;
- prompt compaction is exactly ≤12,000 characters;
- runtime provider wrappers honor persisted provider circuit state before vendor calls;
- GitHub Models remains an emergency fallback with its own circuit breaker;
- regression tests assert the AI budget, bounded Gemini request timeout and exact prompt length.

## Gemini rate-limit hardening — deployed

The production Gemini adapter is deliberately conservative:

- minimum **5 seconds between Gemini requests**;
- bounded exponential retry for **transient** 429 responses: 2s → 4s → 8s → 16s;
- explicit `quota_exceeded` / daily-quota responses are not retried and immediately open the provider circuit;
- prompts are bounded to `12,000` characters;
- provider circuits prevent an exhausted provider from consuming the production budget repeatedly.

Google's current documentation states that Gemini limits are model/tier/project dependent and can apply across RPM, input TPM and RPD. The implementation therefore does not assume a universal RPM value.

## Live evidence before the latest timeout

Production run #792 (`34316757631`) was the first post-fix live discovery run:

- 35/35 regression tests passed;
- discovery executed;
- 499 raw items → 26 candidates;
- `CANONICAL_PRE_AI_FILTER 26 -> 26 threshold 40.0` confirmed the canonical gate;
- Gemini 429 failed immediately with no retry loop;
- Gemini circuit opened for six hours;
- workflow completed normally rather than timing out;
- 8 new candidates entered the durable queue.

All original AI vendors were unavailable at that moment, so the run published 0. GitHub Models fallback was deployed afterward.

## Latest failed run — concrete evidence

Run #834 (`34346240698`) demonstrated that Gemini can remain healthy without 429 retry storms, but the engine still needed a cycle-level evaluation budget:

- regression tests: **38/38 OK**;
- discovery: **799 total raw items**;
- canonical candidates: **43**;
- Gemini: successful throughout the observed sequence;
- no provider-quota retry storm;
- failure point: explicit command timeout, **exit code 124**;
- analytics and state persistence still executed after the engine step failed.

This is classified as a workflow-budget defect, not a Gemini quota defect.

## Live verification — run #847

Run #847 (`34363454469`) is the first production run on the fully deployed performance hardening commit `3db7ea5a514e751868098fe1b0fd783cf10b4f39`.

Verified directly from GitHub Actions:

- workflow event: `workflow_dispatch`;
- run conclusion: **success**;
- production job conclusion: **success**;
- production engine step (`Запуск новостного двигателя`): **success**;
- engine runtime: approximately **54 seconds** (`14:25:11Z` → `14:26:05Z`);
- no `timeout 240s` / exit-124 termination;
- analytics and state-persistence steps completed successfully;
- publisher analytics were persisted by bot commit `fd0b788e9afa70469fef7a29e9f49cdf7d623c29` immediately after the run.

The persisted state from that run contains finalized items with real audience scores and final scores, and the queue-score audit reports `invariant_ok: true` for the persisted production state. The latest inspected persisted analytics also show a healthy Gemini provider state in the successful cycle.

**What is not claimed yet:** the available GitHub Actions metadata does not expose the complete raw production log in the current connector surface, so this verification does not independently prove every log-level acceptance item such as the exact `AI_EVALUATION_SUMMARY` line or the exact number of AI evaluations started in #847. Those remain explicit acceptance checks for the next observable cycle.

## Regression coverage

The workflow runs the scoring, audience, image, Google News, runtime-guard and production-entrypoint regression suites before production execution.

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
- Gemini prompts are exactly bounded to the configured maximum;
- Gemini request timeout is bounded;
- AI evaluation has an explicit workflow safety budget;
- GitHub Models fallback uses the documented OpenAI-compatible endpoint.

## Current commits

- `3db7ea5a514e751868098fe1b0fd783cf10b4f39` — provider cooldown correction; used by verified run #847.
- `c767c7c5681399ce463065abe85e4ca7c37a71d4` — bounded AI evaluations and provider-outage fast stop.
- `add990ba2de8bc4b6ec0d875967e49f3cee1d1ee` — regression coverage for AI evaluation cap/provider halt.
- `72bc6992d41bcfc72c96b9350399dd729dc34d57` — production performance-fix documentation.
- `438982e9d3386f2df8eda9ba4c6666c258d5d197` — final-score queue ordering guard.
- `fb1cda0016d53bb63bc6f0e4457e284a789857be` — finalized-vs-pending ordering regression test.
- `6fbc091907051e1961787100d085c858b802702c` — hardened production entrypoint: canonical pre-AI gate and Gemini fail-fast.
- `bdd599bc87991bdafaf5b5413e2adf6f6fa69c7a` — GitHub Models emergency AI fallback.
- `c1424cd1bdde405a7d4fbc9f184048b532e37fdc` — Gemini 5-second throttle, transient-429 backoff and prompt bound.
- `480624a32cd9815dea9c36f9b0a60d11a138b471` — regression coverage for quota/transient 429 and prompt bound.
- `dd70879969f56ea3743cb870fe2aedfdc5d76bd0` — shared 180-second AI evaluation budget and bounded Gemini request timeout.
- `c715c567d0a17d415b84a2d7a728200fbb521318` — runtime guard stops new model evaluations before workflow timeout.
- `0509efe66c311f4f4dcead7d3f3aedd40a1aff47` — regression coverage for workflow budget, timeout and exact prompt bound.
- `a2f937926abe362885add5ead61050770de205ff` — runtime provider circuit checks restored before vendor calls.

## Remaining acceptance test

The next observable production cycle must demonstrate all of the following in one run:

1. fresh discovery completes;
2. canonical pre-AI gate is 40, without geographic/random score bonus;
3. at least one candidate receives a real AI audience score through a healthy vendor or GitHub Models fallback;
4. provider failure is fail-fast and does not consume the workflow budget;
5. the 180-second AI evaluation deadline is honored and the workflow does not exit 124;
6. final scores are persisted;
7. durable queue ordered by final score, not geography or editorial heuristics;
8. `В очереди` matches the actual top item/score that publication will select;
9. highest finalized score is published;
10. no finalized item below 55 remains in durable queue;
11. footer values exactly match persisted components;
12. no editorial text is truncated;
13. `AI_EVALUATION_SUMMARY` is visible in the production log;
14. real AI evaluation count is ≤10 for the cycle.

Until this live acceptance cycle passes with observable log-level evidence, status remains **YELLOW**.
