# INTILY Project Status — 2026-09-10

## Canonical current status

**🟡 PRODUCTION VERIFICATION MODE — fresh discovery is healthy; queue-gate invariants remain healthy; current AI provider pool is unavailable; provider publication fast-stop has been fixed and needs live verification before GREEN.**

This document supersedes the older 2026-09-09 status for the current operational state. Historical documents remain useful for incident context.

## Current production contract

`Cloudflare intily-ai-news scheduler → GitHub Actions workflow_dispatch → Python production entrypoint → Telegram → durable GitHub state`.

The mathematical editorial contract remains:

`deterministic base 0–70 → AI audience +3…+30 → final 0–100 → queue/publication by final score descending`.

Pre-AI admission threshold: **40.0**.

Final publication gate: **55.0**.

Geography is not part of the mathematical score.

## Latest live verification — run #895

GitHub Actions run `34443365835` completed successfully.

### Discovery

- 64/64 Google News queries succeeded.
- 9/10 direct RSS feeds succeeded.
- VentureBeat AI returned HTTP 429; it was the only direct-feed error.
- 519 raw items were collected.
- 463 were removed by the deterministic score filter.
- 22 were removed by quality/relevance filtering.
- 7 were collapsed as story duplicates.
- 27 candidates remained.
- canonical pre-AI filter: 27 → 27 at threshold 40.0.
- discovery completed in roughly 29 seconds from first query to ingest summary.

This confirms the previously required **fresh-discovery acceptance** on the ingestion side.

### AI/provider layer

The current production state has no usable provider:

- Gemini circuit-open;
- Groq circuit-open;
- OpenAI circuit-open;
- GitHub Models circuit-open.

Run #895 started one real AI evaluation, then emitted:

`AI_EVALUATION_SUMMARY started 1 limit 10 provider_halted True`

No real audience score was produced in that cycle, so the full acceptance test is **not passed**.

## Newly discovered runtime defect

The runtime guard stopped further AI evaluations correctly, but the legacy publisher's local publication-attempt loop was independent of that guard. During provider outage it continued attempting editorial processing for additional queue items.

Run #895 therefore recorded 10 publication attempts and 10 item failures with the same provider-unavailable condition.

This was wasteful but did not cause a workflow timeout or corrupt the durable queue.

## Fix deployed

`65cc5fe0131e6697a3d75f61673739a3aedc102c`

### Provider outage publication fast-stop

`scripts/intily_scoring_runtime_guard.py` now:

- propagates provider-runtime halt into the legacy publication loop;
- sets the process-local publication attempt cap to zero after provider outage;
- prevents the wrapped editorial path from starting another AI edit after halt;
- emits `PUBLICATION_HALTED provider_runtime_unavailable`;
- preserves the existing 10-evaluation cap and 180-second AI safety budget.

Regression test:

`817daff3facd1083fd099f591b3f808b743f1bbf`

`test_provider_outage_halts_legacy_publication_loop`.

## Queue integrity

The queue-gate purge remains verified from run #881:

- `pre_ai_below_final_threshold: 0`;
- `final_below_threshold: 0`;
- `QUEUE_SCORE_AUDIT.invariant_ok: true`;
- finalized items below 55 are not durable.

The latest run #895 also reported `final_below_threshold: 0` and `invariant_ok: true`.

## Tests

Run #895 executed the pre-production regression suite successfully:

- **42/42 tests OK** before the new fast-stop regression was committed.
- The new fast-stop test is now on `main` and must be verified by the next Action run.

## Provider availability

The current persisted provider cooldowns are not bypassed blindly. This is intentional. Repeated calls to exhausted providers waste the production safety budget and can amplify an outage.

Current Gemini handling remains conservative: bounded retry/backoff, request timeout, prompt bound and persisted circuit state. Google's current Gemini documentation states that rate limits vary by model/project/tier and are measured across RPM, TPM and RPD; quota/rate-limit failures should use bounded retry/backoff.

## Next acceptance gate

The next production run must demonstrate:

1. new regression suite passes;
2. fresh discovery still completes;
3. provider outage fast-stops publication attempts rather than repeating across the queue;
4. `AI_EVALUATION_SUMMARY` is present;
5. real AI evaluation count remains ≤10;
6. no `exit 124` / workflow timeout;
7. final queue invariant remains true;
8. once a provider is healthy, at least one real audience score is generated;
9. highest finalized score is published to Telegram;
10. score footer matches persisted components;
11. state and analytics persist.

**Until a healthy provider produces a real audience score and a publication succeeds, the overall production status remains YELLOW.**

## Forward plan after GREEN

After the AI/provider acceptance closes, proceed with the already planned performance work:

1. bounded I/O concurrency for discovery, preserving query order, source telemetry and per-feed time budgets;
2. deterministic upper-bound pruning before AI calls;
3. two-stage AI editorial triage to spend model calls only on candidates capable of clearing the 55 gate;
4. improve provider redundancy so a single vendor outage does not stop editorial publication.
