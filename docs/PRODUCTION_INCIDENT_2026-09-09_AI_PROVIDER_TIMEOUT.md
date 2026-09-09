# INTILY — Production Incident 2026-09-09: AI Provider Timeout and Pre-AI Gate Drift

## Incident 1 — provider retry storm

A production run ingested a large fresh RSS/Google News batch but terminated with exit code 124. The run repeatedly attempted Gemini after HTTP 429 quota exhaustion, while Groq was already circuit-open (`403/1010`) and OpenAI was blocked. The repeated Gemini backoff consumed the five-minute workflow budget.

Observed sequence:

- `GEMINI_RETRY 429 5`
- `GEMINI_RETRY 429 10`
- `GEMINI_RETRY 429 20`
- `AI_PROVIDER_FAILED GEMINI GEMINI_HTTP_429: You exceeded your current quota...`
- provider circuits for Groq/OpenAI
- repeated editorial QA failures
- workflow ended with `exit code 124`

## Incident 2 — pre-AI scoring contract drift

The legacy collector still used `IMPORTANCE_THRESHOLD = 60.0` even though the canonical production contract requires a **40/100 pre-AI gate**. It also added a random Russian-region score bonus before filtering.

Observed in the earlier incident run:

- raw items: 496
- score filtered: 449
- quality filtered: 4
- story dedup: 16
- candidates: 27

This was a material contract drift: the collector was making a 60-point admission decision before the guarded canonical scoring stage.

## Incident 3 — latest workflow-budget timeout

After the Gemini fail-fast and fallback hardening, run **#834 (`34346240698`)** exposed a different failure. The regression suite passed **38/38**, fresh discovery produced **43 candidates**, and Gemini successfully evaluated candidates. However, the production command still had a hard `timeout 240s`, while the runtime had no cycle-level bound on the number of AI evaluations.

With a 5-second Gemini spacing guard, serial evaluation of dozens of candidates can consume most or all of the workflow budget even when the provider is perfectly healthy. The run reached the 42nd AI evaluation and then ended with:

`Process completed with exit code 124.`

The analytics and state-persistence steps still ran, but the news engine never reached its normal queue/publish completion path. This explains the apparent “news disappeared” behavior: discovery worked, but the process was killed before durable admission/publication completed.

## Root causes

1. Gemini previously treated every HTTP 429 as retryable and slept 5/10/20 seconds per affected item.
2. Gemini quota exhaustion was not classified as a provider circuit condition.
3. Legacy provider code had a disabled circuit-check path, so persisted provider blocks were not reliably respected.
4. The legacy collector still had a 60-point threshold, inconsistent with the canonical 40-point pre-AI gate.
5. Legacy collection still applied a random geographic score bonus before filtering.
6. **AI evaluation had no shared cycle-level deadline**, so a healthy provider plus many candidates could exceed the workflow timeout.

## Corrections deployed

`scripts/intily_production_entrypoint.py` remains the canonical runtime entrypoint before the scoring guard.

It now:

- forces the pre-AI threshold to 40;
- removes the legacy Russian random bonus before canonical scoring;
- recalculates candidates using the canonical score function;
- drops candidates whose true deterministic base is below 40;
- enforces a minimum 5-second interval between Gemini requests;
- retries only transient Gemini 429s with bounded exponential backoff: 2s → 4s → 8s → 16s;
- identifies `quota_exceeded`, daily-quota and equivalent exhausted-quota responses and does **not** retry them;
- opens a six-hour Gemini circuit on exhausted quota;
- bounds Gemini/GitHub Models editorial prompt input to exactly `≤12,000` characters;
- adds GitHub Models (`models: read`) as an emergency AI fallback when vendor APIs fail;
- circuit-breaks GitHub Models after a hard fallback failure;
- restores provider-circuit checks at runtime before Gemini/Groq/OpenAI calls, even though the legacy provider path contains a disabled check;
- introduces a **shared 180-second AI evaluation deadline** covering both pending-queue finalization and fresh candidates;
- stops starting new model calls when the deadline is reached, leaving remaining material as `pre_ai` so normal queue handling and state persistence can finish;
- reduces the direct Gemini request timeout to 20 seconds.

The runtime guard therefore has two independent protections:

`provider circuit → request/backoff bound → shared cycle AI deadline → workflow timeout`

The workflow's explicit 240-second production command remains the outer safety net, not the normal control mechanism.

## Current Gemini guidance verified against official documentation

Google's current documentation states that Gemini rate limits are project/model/tier dependent and can involve RPM, input TPM and RPD. It distinguishes transient `rate_limit_exceeded` / `too_many_requests` from `quota_exceeded`: transient errors should use exponential backoff, while exhausted daily quota should wait for reset or receive a quota increase. citeturn1search2turn1search1turn1search3

Therefore INTILY deliberately does **not** assume that every 429 means exactly 15 RPM. The 5-second local spacing is a conservative protection; the returned error body determines whether retrying is appropriate.

## Live verification after first hardening

Production run #792 (`34316757631`) showed:

- 35/35 regression tests passed;
- discovery executed successfully;
- 499 raw items were ingested;
- 26 candidates were produced;
- Gemini 429 failed immediately without a retry loop;
- Gemini circuit opened for 6 hours;
- the workflow completed without timeout;
- 8 new candidates entered the durable queue.

That run published 0 because all three original providers were unavailable and GitHub Models fallback had not yet been deployed at that moment.

## Latest failed run — #834

Run #834 (`34346240698`) provided the next diagnostic signal:

- 38/38 regression tests: **OK**;
- 799 total raw items;
- 43 canonical candidates;
- Gemini successfully handled the observed candidate evaluations;
- no Gemini quota retry storm;
- process terminated by the explicit 240-second command timeout;
- exit code: **124**;
- failure classification: **unbounded AI evaluation**, not provider quota exhaustion.

## Verification required

The next production run must verify all of the following:

1. Gemini request spacing is respected;
2. transient 429 retry is bounded and quota exhaustion is fail-fast;
3. persisted provider circuits prevent calls to blocked vendors;
4. GitHub Models fallback is reachable when primary vendors fail;
5. the 180-second AI evaluation budget stops new model work before the workflow timeout;
6. fresh discovery completes and its candidates are not lost merely because some remain `pre_ai`;
7. canonical pre-AI 40 gate is actually used;
8. final-score queue ordering remains correct;
9. highest finalized score is published;
10. no final score below 55 remains in the durable queue;
11. state/analytics persistence completes without exit 124;
12. footer values exactly match persisted components;
13. no editorial text is truncated.

Status remains **YELLOW until this live acceptance cycle passes**.