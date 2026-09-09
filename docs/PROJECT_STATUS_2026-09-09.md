# INTILY Project Status — 2026-09-09

## Canonical current status

**🟡 PRODUCTION VERIFICATION MODE — performance/provider hardening is live; queue-gate purge is deployed and verified in production run #881; one fresh discovery-cycle acceptance run is still required before GREEN.**

This document is the canonical current status. The production contract remains: deterministic base 0–70 → AI audience +3…+30 → final 0–100 → queue/publication ordered by final score descending. Geography is not part of the mathematical score.

## Verified defect and correction — queue ordering

The previous queue implementation had three paths that could make the user-visible queue diverge from the agreed final-score contract:

1. finalized and pending `pre_ai` items were sorted in one numeric field (`importance`), so a pending base score could outrank an already-finalized lower score;
2. the legacy `rebalance_queue()` enforced a regional quota before final sorting and could displace a higher-scoring story;
3. the publication priority was guarded, but the legacy regional candidate selection and rebalance remained separate ordering authorities.

The runtime guard now has one ordering authority:

`AI final score → queue ranking → publication priority`.

Changes in `scripts/intily_scoring_runtime_guard.py`:

- final items always outrank pending `pre_ai` items;
- among finalized items, `final_score` is the primary key and timestamp is only a tie-breaker;
- the legacy regional quota rebalance is bypassed in production in favor of pure score-capacity rebalance (`MAX_QUEUE`);
- pre-AI items cannot outrank finalized items during publication selection;
- finalized items below the **55.0 publication gate are explicitly removed from the durable queue**;
- pre-AI 40–54 items remain valid queue candidates until AI editorial review;
- score footer remains complete and non-truncating.

This last rule was added after live run #880 exposed **2 finalized queue items below 55**, violating the documented invariant. The correction was deployed in `54f10ea6e7212e253353cdc69f7583522c7f78e1`.

## Production incident — AI evaluation exceeded workflow budget

The failed Action was run #834 (`34346240698`), commit `5d7993c03ac6e66e452c3831bc2fe8c0fa9fa398`. The publish job failed in the production engine step after the regression suite completed 38/38 OK; analytics and state persistence still executed.

The production engine performed a fresh search and produced 43 candidates. Gemini was healthy, but the runtime evaluated candidates serially at the conservative 5-second request spacing. The run reached 42 AI evaluations and was killed by the explicit `timeout 240s` wrapper with `exit code 124` before queue/publication could complete.

This exposed a second-order design defect: provider rate limiting was bounded, but the number of AI evaluations was not bounded.

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
- explicit quota/daily-quota responses are not retried and immediately open the provider circuit;
- prompts are bounded to `12,000` characters;
- provider circuits prevent an exhausted provider from consuming the production budget repeatedly.

## Live verification — run #880 → #881

Run #880 (`34392418735`) on the pre-purge runtime exposed the exact remaining invariant violation:

- 58 candidates after ingestion;
- 9 real AI evaluations started before provider runtime became unavailable;
- `AI_EVALUATION_SUMMARY started 9 limit 10 provider_halted True` was emitted;
- workflow completed successfully without `exit 124`;
- however, `QUEUE_SCORE_AUDIT` reported `final_below_threshold: 2` and `invariant_ok: false`.

The queue-gate correction was then deployed as `54f10ea6e7212e253353cdc69f7583522c7f78e1`.

Run #881 (`34393036299`) is the first live production verification of that correction:

- workflow: **success**;
- production job: **success**;
- production engine: **success**;
- commit executed: `54f10ea6e7212e253353cdc69f7583522c7f78e1`;
- regression suite: **41/41 OK**;
- AI evaluation budget: **180s**;
- real AI evaluations started: **4**;
- Gemini successfully evaluated all four items in this cycle;
- one Telegram publication succeeded (`TELEGRAM_SENT`);
- queue after publication: **12**;
- `QUEUE_SCORE_AUDIT`: `pre_ai_below_final_threshold: 0`, `final_below_threshold: 0`, **`invariant_ok: true`**;
- no `timeout 240s` / exit 124.

This is strong evidence that the queue-gate correction works in production.

Run #881 was a queue-drain cycle (`SEARCH_SKIPPED` because fresh discovery was not due yet), so it does **not** by itself close the full fresh-discovery acceptance. The next discovery cycle must be checked for the same invariants plus candidate evaluation telemetry.

## Scheduler/runtime observation

The repository contract intentionally keeps GitHub Actions as `workflow_dispatch` only; Cloudflare is the scheduler. The current Worker source declares a minutely Cron and a randomized 1-in-3 dispatch gate, while collection itself is separately throttled by the publisher's durable state.

Observed live runs #880 and #881 at `19:00Z` and `19:06Z` confirm that the Cloudflare → GitHub dispatch path is currently producing production runs at the expected approximate cadence. No second GitHub scheduler was introduced.

## Discovery performance

The latest fresh discovery run #880 processed:

- 64/64 Google News queries successfully;
- 9/10 direct RSS feeds successfully;
- VentureBeat AI remained the only direct-feed error (`HTTP 429`);
- 1,507 raw items;
- 58 candidates;
- roughly 36 seconds for serial discovery before candidate processing.

This is now the next optimization target, but **not** a production-breaking defect. The planned optimization remains bounded I/O concurrency for discovery, followed later by deterministic upper-bound pruning and a two-stage AI architecture.

## Current production quality observations

Run #881 confirms the core publication path is healthy, but two non-blocking quality signals remain under observation:

1. **Image fallback:** the selected source image was unavailable/blocked, so the publisher correctly used text fallback rather than truncating the post.
2. **Provider resilience:** Gemini can temporarily return timeout/503; the runtime now stops starting new evaluations once the provider circuit opens. In #880 this occurred after 9 evaluations and did not break the workflow.

The 24h monitor still reports a historically high item-failure ratio because it aggregates older degraded cycles. This is not treated as a current single-run failure; it remains an operational KPI to reduce as provider availability stabilizes.

## Regression coverage

The workflow currently runs the scoring, audience, image, Google News, runtime-guard and production-entrypoint regression suites before production execution.

Coverage includes:

- no legacy +10 pre-AI audience placeholder;
- AI 10/10 contribution reaches +30;
- final score is primary ordering key;
- finalized items outrank pending pre-AI items;
- finalized items below 55 are rejected from durable queue;
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

- `54f10ea6e7212e253353cdc69f7583522c7f78e1` — purge finalized stories below publication gate; verified by run #881.
- `3e143b79e5a5ed1a869216c98fc4551af319b7e0` — regression test for finalized queue gate.
- `3db7ea5a514e751868098fe1b0fd783cf10b4f39` — provider cooldown correction; used by run #847 and later cycles.
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

The next **fresh discovery** production cycle must demonstrate all of the following in one run:

1. fresh discovery completes;
2. canonical pre-AI gate is 40, without geographic/random score bonus;
3. at least one candidate receives a real AI audience score through a healthy vendor or GitHub Models fallback;
4. provider failure is fail-fast and does not consume the workflow budget;
5. the 180-second AI evaluation deadline is honored and the workflow does not exit 124;
6. `AI_EVALUATION_SUMMARY` is visible;
7. real AI evaluation count is ≤10;
8. final scores are persisted;
9. durable queue ordered by final score, not geography or editorial heuristics;
10. `В очереди` matches the actual top item/score that publication will select;
11. highest finalized score is published;
12. `QUEUE_SCORE_AUDIT.invariant_ok` is true;
13. no finalized item below 55 remains in durable queue;
14. footer values exactly match persisted components;
15. no editorial text is truncated;
16. state/analytics persist successfully.

Until this fresh-discovery acceptance cycle passes, status remains **YELLOW**. After it passes, the next planned engineering step is discovery I/O concurrency; after performance acceptance, deterministic upper-bound pruning and two-stage AI editorial triage remain the forward architecture.
