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
- leaves other providers to the existing failover logic;
- prevents one exhausted provider from consuming the entire five-minute production budget.

The workflow now runs `scripts/intily_production_entrypoint.py` and includes its regression test.

## Provider evidence

Google's current Gemini API documentation distinguishes `quota_exceeded` 429 errors from transient rate-limit conditions and recommends backoff only where retry is appropriate. The production error text explicitly reported exhausted current quota, so treating that response as a long per-item retry loop was incorrect for this runtime. citeturn1search0turn0search0

## Verification required

The fix is committed and covered by a regression test for the one-shot 429 path. A fresh production run must still verify:

1. no repeated `GEMINI_RETRY` loop after quota exhaustion;
2. provider circuit opens after the first quota failure;
3. workflow completes within the normal budget;
4. canonical pre-AI 40 gate is actually used;
5. new-search candidates are AI-evaluated when a provider is available;
6. final-score queue ordering remains correct;
7. highest finalized score is published;
8. no final score below 55 remains in the durable queue.

Status remains **YELLOW until live verification**.
