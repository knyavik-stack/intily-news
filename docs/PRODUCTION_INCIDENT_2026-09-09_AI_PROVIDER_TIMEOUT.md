# INTILY — Production Incident 2026-09-09: AI Provider Timeout and Pre-AI Gate Drift

## Incident

A production run ingested a large fresh RSS/Google News batch but terminated with exit code 124. The run repeatedly attempted Gemini after HTTP 429 quota exhaustion, while Groq was already circuit-open (`403/1010`) and OpenAI was blocked. The repeated Gemini backoff consumed the five-minute workflow budget.

Observed sequence:

- `GEMINI_RETRY 429 5`
- `GEMINI_RETRY 429 10`
- `GEMINI_RETRY 429 20`
- `AI_PROVIDER_FAILED GEMINI GEMINI_HTTP_429: You exceeded your current quota...`
- `AI_PROVIDER_BLOCKED GROQ ...`
- `AI_PROVIDER_BLOCKED OPENAI ...`
- repeated editorial QA failures
- workflow ended with `exit code 124`

## Second defect exposed by the same run

The legacy collector still used `IMPORTANCE_THRESHOLD = 60.0` even though the canonical production contract requires a **40/100 pre-AI gate**. It also added a random Russian-region score bonus before filtering. Therefore the ingestion telemetry could not faithfully represent the canonical scoring model.

The observed run showed:

- raw items: 496
- score filtered: 449
- quality filtered: 4
- story dedup: 16
- candidates: 27
- score buckets: 416 below 40; 37 in 40–49; 39 in 50–59; 4 in 60–69

This is a material contract drift: the collector was making a 60-point admission decision before the guarded canonical scoring stage.

## Root causes

1. Gemini treated every HTTP 429 as retryable and slept 5/10/20 seconds for each item.
2. Gemini quota exhaustion was not classified as a provider circuit condition.
3. The provider failover chain had no fast cycle-level failure path when all providers were unavailable.
4. Legacy collection still had a 60-point threshold, inconsistent with the canonical 40-point pre-AI gate.
5. Legacy collection still applied a random geographic score bonus before filtering.

## Correction

Added `scripts/intily_production_entrypoint.py` as the canonical runtime entrypoint before the scoring guard.

It now:

- forces the pre-AI threshold to 40;
- removes the legacy Russian random bonus before canonical scoring;
- recalculates candidates using the canonical score function;
- drops candidates whose true deterministic base is below 40;
- replaces Gemini's multi-retry path with a single request;
- detects Gemini 429 quota exhaustion and opens a six-hour circuit for that provider;
- adds GitHub Models (`models: read`) as an emergency AI fallback when Gemini, Groq and OpenAI are unavailable;
- circuit-breaks GitHub Models after a hard fallback failure so an unavailable fallback cannot create another timeout loop;
- prevents one exhausted provider from consuming the five-minute production budget.

The workflow already has `models: read`, which is the documented permission required by GitHub's current AI inference tooling. GitHub's current AI inference documentation exposes the GitHub Models REST endpoint and confirms that GitHub Models can be used from Actions with `models: read`. citeturn5search1turn5search6

## Provider evidence

Google's current Gemini API documentation distinguishes `quota_exceeded` 429 errors from transient rate-limit conditions and recommends backoff only where retry is appropriate. The production error text explicitly reported exhausted current quota, so treating that response as a long per-item retry loop was incorrect for this runtime. citeturn1search0turn0search0

## Live verification after first hardening

The first post-fix run (#792, `34316757631`) is important evidence:

- 35/35 regression tests passed;
- discovery executed successfully;
- 499 raw items were ingested;
- 26 candidates were produced;
- the Gemini 429 failed immediately without `GEMINI_RETRY`;
- Gemini circuit opened for 6 hours;
- the workflow completed in seconds rather than timing out;
- 8 new candidates entered the durable queue.

That run still published 0 because, at that moment, all three original providers were unavailable and the GitHub Models fallback had not yet been deployed. This proves the timeout defect is fixed, but not yet the full AI-publication path.

## Verification required

The next production run must verify:

1. GitHub Models fallback is actually reachable with the workflow's `models: read` permission;
2. at least one candidate receives a real AI audience score through the fallback if vendor APIs remain unavailable;
3. no repeated provider retry loop occurs;
4. workflow completes within the normal budget;
5. canonical pre-AI 40 gate is actually used;
6. new-search candidates are AI-evaluated when a provider is available;
7. final-score queue ordering remains correct;
8. highest finalized score is published;
9. no final score below 55 remains in the durable queue.

Status remains **YELLOW until this live provider/publication verification passes**.
