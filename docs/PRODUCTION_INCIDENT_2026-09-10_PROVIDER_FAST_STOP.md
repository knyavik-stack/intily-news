# INTILY Production Incident — 2026-09-10 Provider Fast-Stop

## Status

**YELLOW — fresh discovery works, but the current production AI provider pool is unavailable. A runtime defect that repeated the same provider failure across the publication queue has been fixed and is awaiting live verification.**

## Evidence

### Run #895

GitHub Actions run `34443365835` (`Intily AI News Publisher`) completed successfully at approximately 06:01 UTC.

Fresh discovery acceptance signals:

- 64/64 Google News queries succeeded.
- 9/10 direct RSS feeds succeeded.
- VentureBeat AI returned HTTP 429; this is the only direct-feed error in the cycle.
- 519 raw items were collected: 467 Google News items + 52 direct RSS items.
- 463 items were removed by the deterministic pre-AI score filter.
- 22 were removed by quality/relevance filtering.
- 7 were collapsed as story duplicates.
- 27 candidates remained after ingestion.
- canonical pre-AI filter retained all 27 candidates at threshold 40.0.
- discovery completed without workflow timeout.

AI/provider state in the same run:

- 1 real AI evaluation was started before the provider runtime was declared unavailable.
- Gemini, Groq and OpenAI were all persisted as circuit-open.
- GitHub Models was also blocked by its persisted cooldown.
- `AI_EVALUATION_SUMMARY started 1 limit 10 provider_halted True` was emitted.
- No candidate received a real audience score in this cycle.
- Telegram publication count was 0.

## Defect discovered

The runtime guard correctly stopped starting new AI evaluations after `AI_PROVIDERS_UNAVAILABLE`, but the legacy publisher owned a separate local `MAX_ATTEMPTS_PER_RUN` loop. Because that loop was unaware of the guard's provider-halt flag, it continued calling the editorial `edit()` path for additional queue items.

This caused repeated identical provider failures and inflated the cycle's `publish_attempts` / `item_failures` counters. It did not cause a workflow timeout, but it violated the intended fail-fast contract.

The observed run attempted 10 queue items and all 10 failed with the same provider-unavailable condition.

## Correction

Commit `65cc5fe0131e6697a3d75f61673739a3aedc102c` updates `scripts/intily_scoring_runtime_guard.py`:

- added `_halt_publication_attempts()`;
- when provider runtime becomes unavailable, the legacy publication attempt cap is set to `0` for the current process;
- the wrapped editorial function refuses to start another AI edit after provider halt;
- queue precheck, candidate evaluation and publication paths all propagate the same provider-halt state;
- a `PUBLICATION_HALTED provider_runtime_unavailable` telemetry marker is emitted;
- the existing AI evaluation cap of 10 and 180-second budget remain unchanged.

Commit `817daff3facd1083fd099f591b3f808b743f1bbf` adds regression coverage for the publication-loop fast stop.

## Why this is the correct behavior

When no AI provider is usable, INTILY must preserve the durable queue and state, stop spending time on doomed editorial calls, and wait for a later cycle/provider recovery. It must not mark multiple unrelated queue items as failed merely because the provider pool is globally unavailable.

The publisher therefore remains safe to run during provider outage, but it must not be considered GREEN until a healthy AI provider produces a real audience score and a publication is successfully delivered.

## Next live verification

The next production run must confirm:

1. regression suite passes with the new fast-stop test;
2. provider outage causes at most the already-started editorial attempt to fail, with no repeated queue-wide provider attempts;
3. `PUBLICATION_HALTED provider_runtime_unavailable` appears when the provider pool is unavailable;
4. fresh discovery remains functional;
5. `AI_EVALUATION_SUMMARY` remains present on fresh cycles;
6. no workflow timeout / exit 124 occurs;
7. `QUEUE_SCORE_AUDIT.invariant_ok` remains true;
8. once any provider recovers, at least one real AI audience score is produced and the highest finalized item can reach Telegram.

## Provider recovery note

The current persisted Gemini cooldown is approximately six hours after a quota/rate-limit event, while Groq, OpenAI and GitHub Models also have persisted cooldowns from prior failures. The code does not bypass those circuits blindly. This is intentional: repeatedly calling an exhausted provider wastes the production budget and can prolong an outage.

Google's current Gemini documentation confirms that rate limits are project/model/tier dependent and can be constrained by RPM, TPM and RPD; `429` quota/rate-limit responses should be handled with bounded retry/backoff rather than unlimited retries.
