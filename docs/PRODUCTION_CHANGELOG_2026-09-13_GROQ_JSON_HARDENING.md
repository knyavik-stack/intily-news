# INTILY production changelog — 2026-09-13 — Groq GPT-OSS JSON hardening

## Incident

Several recent production runs completed green at the GitHub Actions level but published no Telegram post.

The latest observed run before this fix was **Intily AI News Publisher #1199**. It had 11 durable queue items, including one high-score item, but publication stopped during AI editorial evaluation because:

- Gemini was in a persisted circuit-open state after prior provider failures;
- OpenAI was also circuit-open due the existing no-credit/quota condition;
- the Groq fallback was available but returned an empty/invalid editorial response;
- the runtime then halted further publication attempts by design.

This was **not** caused by an oversized state file. The publisher state is bounded by explicit retention rules: published history is pruned to 30 days, semantic story history to 24 hours, known RSS memory to 90 minutes, and KPI history to 200 runs.

## Evidence

Run #1199 logs showed:

- `AI_PROVIDER_BLOCKED GEMINI 985`
- `AI_PROVIDER_OK GROQ`
- `EDITORIAL_QA_FAILED ... Expecting value: line 1 column 1 (char 0)`
- second candidate: `AI_PROVIDER_FAILED GROQ EMPTY_RESPONSE`
- `AI_PROVIDER_BLOCKED OPENAI ...`
- `PUBLICATION_HALTED provider_runtime_unavailable`
- queue remained at 11 items and `BUSINESS_RESULT NO_PUBLISH no_eligible_item`.

The same failure pattern had appeared in the preceding production window: Groq was being used as the practical fallback after Gemini failures, but the GPT-OSS response contract was not hardened for structured JSON generation.

## Root cause

The production Groq request used the legacy OpenAI-compatible `max_tokens` parameter and did not explicitly configure GPT-OSS reasoning/output behavior. The runtime expected `choices[0].message.content` to contain the complete JSON document.

Groq's current GPT-OSS documentation recommends `max_completion_tokens` for these reasoning models and supports `include_reasoning: false` plus JSON response mode. The production request did not use that contract.

Official Groq documentation:
- https://console.groq.com/docs/reasoning
- https://console.groq.com/docs/structured-outputs
- https://console.groq.com/docs/model/openai/gpt-oss-20b

## Fix

Commit `75132f60e8a19d9cbb296c6c90e40c81fcc039fc`:

- switched Groq GPT-OSS request from `max_tokens` to `max_completion_tokens=1200`;
- set `include_reasoning=false` so reasoning content does not consume the expected editorial output channel;
- enabled `response_format={"type":"json_object"}`;
- explicitly reject empty `message.content` as `GROQ_EMPTY_CONTENT`;
- preserved existing timeout, quota, 403/1010 and retry protections.

Commit `badc867a393156a78a80eac7ac679299606343dc` adds regression coverage for the exact request contract and empty-content failure.

## Safety / scope

- Cloudflare Worker was **not touched**.
- Editorial prompt was **not changed**.
- Scoring thresholds were **not changed**.
- Queue retention policy was **not weakened**.
- No production state was manually deleted or reset.
- The fix is limited to the Groq fallback transport/structured-output contract and its regression test.

## Verification requirement

The next production run must prove all of the following in logs:

1. `53 tests ... OK` (or a newer complete regression count);
2. `AI_PROVIDER_OK GROQ` when Gemini remains unavailable;
3. no `GROQ EMPTY_RESPONSE` / `GROQ_EMPTY_CONTENT`;
4. `EDITORIAL_QA_OK` for a queue item;
5. `TELEGRAM_SENT <message_id>`;
6. `BUSINESS_RESULT PUBLISHED telegram_delivery_ok`;
7. queue state persists after publication.

A green GitHub Actions conclusion alone is **not** considered proof of publication.
