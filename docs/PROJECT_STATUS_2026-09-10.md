# INTILY Project Status — 2026-09-10

## Canonical current status

**🟡 PRODUCTION VERIFICATION MODE — Gemini is confirmed healthy and Telegram delivery works; OpenAI key rotation is now handled automatically; Groq 403/1010 is identified as a client-signature/Cloudflare edge issue and is being fixed in the HTTP client; fresh-discovery acceptance remains the final gate to GREEN.**

This document supersedes the older 2026-09-09 status for the current operational state. Historical documents remain useful for incident context.

## Current production contract

`Cloudflare intily-ai-news scheduler → GitHub Actions workflow_dispatch → Python production entrypoint → Telegram → durable GitHub state`.

The mathematical editorial contract remains:

`deterministic base 0–70 → AI audience +3…+30 → final 0–100 → queue/publication by final score descending`.

Pre-AI admission threshold: **40.0**.

Final publication gate: **55.0**.

Geography is not part of the mathematical score.

## Root cause found — provider circuit deadlock

Runs #895/#899 did not fail because news discovery or Telegram was broken. Persisted provider circuit state marked Gemini, Groq, OpenAI and GitHub Models as disabled, so the next cycles were blocked before making real vendor requests.

Run #900 used the one-shot recovery utility and proved the real external state:

- **Gemini: GREEN** — multiple real `AI_PROVIDER_OK GEMINI` responses;
- **Groq: RED at that time** — HTTP 403 / Cloudflare code 1010;
- **OpenAI: RED at that time** — HTTP 429, `You have no credits remaining`;
- **GitHub Models: permanently unavailable** — GitHub retired GitHub Models on July 30, 2026.

The recovery cycle then completed end-to-end Telegram publication:

- `TELEGRAM_SENT 1096`;
- `BUSINESS_RESULT PUBLISHED telegram_delivery_ok`;
- `QUEUE_SCORE_AUDIT invariant_ok:true`;
- no workflow timeout.

## Provider architecture correction — 2026-09-10

The former GitHub Models emergency fallback has been removed from production code. It is not a viable fallback because GitHub officially retired the GitHub Models inference service on July 30, 2026. This is a permanent service retirement, not a temporary outage.

The production AI pool is now explicitly:

1. Gemini — primary confirmed provider;
2. Groq — fallback, with a client-side Cloudflare 1010 fix being deployed;
3. OpenAI — fallback, key rotation supplied by Boss and awaiting next live production verification.

### API-key rotation recovery

Production stores only a short SHA-256 fingerprint of each configured provider key in durable state. The secret itself is never persisted.

On first migration, if an existing circuit is present, the provider circuit is reopened once and its current key fingerprint is recorded. On subsequent secret rotation, a changed fingerprint automatically reopens that provider circuit.

This prevents a legitimate API-key replacement from remaining blocked behind a stale 6-hour/24-hour circuit.

## OpenAI status

The workflow reads `secrets.OPENAI_API_KEY`. Secret values are intentionally not inspectable through the GitHub connector.

Boss has replaced the GitHub Actions secret. The next production cycle will detect the changed key fingerprint and clear the stale OpenAI circuit automatically. No API key should be sent through chat.

## Gemini status

Gemini is the confirmed production AI provider. Run #900 produced several successful editorial evaluations and audience scores after the persisted circuit was cleared.

Current runtime keeps bounded timeout, request spacing and retry behavior. Google's current documentation confirms that Gemini limits are project/model/tier dependent and distinguishes transient rate limits from daily quota exhaustion.

## Groq status — root cause identified

The HTTP 403 response contained Cloudflare error code **1010**. This is not evidence that the Groq API key is invalid. Current technical reports show Groq's Cloudflare edge can reject Python `urllib`'s default client signature/User-Agent with 403/1010, while a normal application User-Agent succeeds. Groq's own documentation separately defines ordinary 403s as permission restrictions.

INTILY's generic `chat()` request uses `urllib.request`, so the production request path is susceptible to this exact edge behavior. The correct fix is to send an explicit application User-Agent on Groq requests rather than rotating the key blindly.

The configured model remains `llama-3.1-8b-instant`. After the HTTP-client fix, the next live cycle will be the authoritative Groq probe.

## Queue / publication integrity

Run #900 confirmed:

- final-below-threshold: 0;
- `QUEUE_SCORE_AUDIT.invariant_ok: true`;
- real audience scores generated;
- Telegram delivery confirmed;
- durable queue preserved.

## Tests

The normal CI suite includes provider recovery and API-key rotation regression coverage. The next normal workflow run must verify the updated production entrypoint and the Groq client path.

## Next acceptance gate

The next fresh-discovery cycle must demonstrate:

1. current Google News/direct RSS discovery;
2. canonical pre-AI gate 40;
3. real Gemini and/or newly rotated OpenAI audience evaluation;
4. Groq probe with explicit application User-Agent;
5. `AI_EVALUATION_SUMMARY` with evaluation count ≤10;
6. final-score queue ordering;
7. highest qualifying finalized item published;
8. `QUEUE_SCORE_AUDIT.invariant_ok:true`;
9. no finalized queue item below 55;
10. footer matches persisted score components;
11. state and analytics persist.

Only after this fresh-discovery cycle passes should the incident class return to GREEN.

## Forward plan after GREEN

1. bounded I/O concurrency for discovery while preserving query/source telemetry;
2. deterministic upper-bound pruning before AI calls;
3. two-stage AI editorial triage;
4. retain at least two independently verified AI providers;
5. keep credential-rotation recovery automatic.
