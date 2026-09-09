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

## Corrections deployed

`scripts/intily_production_entrypoint.py` is now the canonical runtime entrypoint before the scoring guard.

It now:

- forces the pre-AI threshold to 40;
- removes the legacy Russian random bonus before canonical scoring;
- recalculates candidates using the canonical score function;
- drops candidates whose true deterministic base is below 40;
- enforces a minimum 5-second interval between Gemini requests;
- retries only transient Gemini 429s with bounded exponential backoff: 2s → 4s → 8s → 16s;
- identifies `quota_exceeded`, daily-quota and equivalent exhausted-quota responses and does **not** retry them;
- opens a six-hour Gemini circuit on exhausted quota;
- bounds Gemini/GitHub Models editorial prompt input to 12,000 characters;
- adds GitHub Models (`models: read`) as an emergency AI fallback when Gemini, Groq and OpenAI are unavailable;
- circuit-breaks GitHub Models after a hard fallback failure so an unavailable fallback cannot create another timeout loop;
- prevents one exhausted provider from consuming the five-minute production budget.

Google's current Gemini documentation states that rate limits are project/model/tier dependent and can involve RPM, input TPM and RPD. It distinguishes transient `rate_limit_exceeded` from `quota_exceeded`: transient limits should use exponential backoff, while exhausted daily quota should wait for reset or receive a quota increase rather than being hammered with retries. citeturn0search0turn0search1turn0search2

Therefore the implementation deliberately does **not** assume that every 429 means exactly 15 RPM. The 5-second spacing is a conservative local guard, while the error body determines whether retrying is appropriate.

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

1. Gemini request spacing is respected;
2. transient 429 retry is bounded and quota exhaustion is fail-fast;
3. GitHub Models fallback is reachable with the workflow's `models: read` permission;
4. at least one candidate receives a real AI audience score through the fallback if vendor APIs remain unavailable;
5. no repeated provider retry loop occurs;
6. workflow completes within the normal budget;
7. canonical pre-AI 40 gate is actually used;
8. new-search candidates are AI-evaluated when a provider is available;
9. final-score queue ordering remains correct;
10. highest finalized score is published;
11. no final score below 55 remains in the durable queue.

Status remains **YELLOW until this live provider/publication verification passes**.
