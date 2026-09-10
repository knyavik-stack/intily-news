# INTILY Project Status — 2026-09-10

## Canonical current status

**🟡 PRODUCTION VERIFICATION MODE — provider incident resolved for Gemini; fresh-discovery acceptance remains the final gate to GREEN.**

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
- **Groq: RED** — HTTP 403 / code 1010;
- **OpenAI: RED** — HTTP 429, `You have no credits remaining`;
- **GitHub Models: RED** — HTTP 410 retirement brownout.

The recovery cycle then completed end-to-end Telegram publication:

- `TELEGRAM_SENT 1096`;
- `PUBLISHED Anthropic Discloses Four Incidents of Claude Models Accessing Real Systems - Hokanews importance 71.0`;
- `BUSINESS_RESULT PUBLISHED telegram_delivery_ok`;
- `QUEUE_SCORE_AUDIT invariant_ok:true`;
- no workflow timeout.

A single Gemini request timed out during the cycle; the following Gemini request succeeded. This is treated as transient provider behavior, not a persistent API block.

## Recovery implementation

Added:

- `scripts/intily_provider_recovery.py` — one-shot operator recovery of persisted provider circuits;
- `scripts/test_intily_provider_recovery.py` — regression coverage;
- `docs/PRODUCTION_INCIDENT_2026-09-10_PROVIDER_ROOT_CAUSE.md` — incident evidence and remediation.

The temporary recovery mode and temporary push trigger were removed immediately after run #900. The normal workflow is again `workflow_dispatch` only.

The recovery utility remains available but is not invoked during normal production cycles.

## OpenAI status

The production workflow reads `secrets.OPENAI_API_KEY`. GitHub secret values are intentionally not inspectable through the connector.

The current secret was actually tested in run #900 and OpenAI returned HTTP 429 with `You have no credits remaining`.

If Boss created a new OpenAI API key, it must be installed as the repository Actions secret `OPENAI_API_KEY`. If that key belongs to an organization/project without available API credits, key rotation alone will not solve the 429.

Do not send API keys through chat.

## Gemini status

Gemini is currently the confirmed production AI provider. Run #900 produced several successful editorial evaluations and audience scores after the persisted circuit was cleared.

Current runtime keeps bounded timeout, request spacing and retry behavior. Google's current documentation confirms that Gemini limits are project/model/tier dependent and distinguishes transient rate limits from daily quota exhaustion.

## Queue / publication integrity

Run #900 confirmed:

- final-below-threshold: 0;
- `QUEUE_SCORE_AUDIT.invariant_ok: true`;
- real audience scores generated;
- Telegram delivery confirmed;
- durable queue preserved.

## Tests

The normal CI suite now includes the provider recovery utility regression test. The live recovery run executed the pre-existing 43-test suite successfully; the new utility test is included in the next normal workflow run.

## Next acceptance gate

The next fresh-discovery cycle must demonstrate:

1. current Google News/direct RSS discovery;
2. canonical pre-AI gate 40;
3. real Gemini audience evaluation;
4. `AI_EVALUATION_SUMMARY` with evaluation count ≤10;
5. final-score queue ordering;
6. highest qualifying finalized item published;
7. `QUEUE_SCORE_AUDIT.invariant_ok:true`;
8. no finalized queue item below 55;
9. footer matches persisted score components;
10. state and analytics persist.

Only after this fresh-discovery cycle passes should the incident class return to GREEN.

## Forward plan after GREEN

1. bounded I/O concurrency for discovery while preserving query/source telemetry;
2. deterministic upper-bound pruning before AI calls;
3. two-stage AI editorial triage;
4. stronger provider redundancy and credential-rotation recovery semantics.
