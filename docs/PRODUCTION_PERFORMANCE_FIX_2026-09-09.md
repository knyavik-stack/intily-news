# INTILY Production Performance Fix — 2026-09-09

## Incident / observation

Production runs `#845` and `#846` showed that discovery itself was healthy, but the editorial AI stage could dominate the cycle time.

Run #845:
- 64/64 Google News queries succeeded.
- 9/10 direct RSS feeds succeeded; VentureBeat AI returned HTTP 429.
- 1181 raw items -> 48 candidates.
- 18 existing queue items were prechecked.
- Gemini successfully evaluated six items before one later request timed out.
- The production engine ran from approximately 13:39:26 to 13:40:52 UTC (~86 seconds), while the full Actions run also included runner/setup and analytics/persistence overhead.
- 1 item was published successfully.

Run #846:
- 1179 raw items -> 49 candidates.
- Gemini returned HTTP 503 (`high demand`) on the first editorial call.
- Groq and OpenAI were already circuit-open.
- GitHub Models returned HTTP 410 with `github_models_retirement_brownout`.
- The runtime then attempted provider evaluation repeatedly for many remaining candidates even though no provider was usable. The job still completed, but published 0 items.

## Root causes

1. Candidate volume is variable (48–49 in these runs) while editorial evaluation was effectively unbounded.
2. Gemini interactive calls are deliberately throttled; the configured 5-second interval already caps the publisher's own Gemini request cadence at 12 RPM, below the project's observed 15 RPM limit.
3. A provider outage was not treated as a cycle-level stop condition. After all providers became unavailable, every remaining candidate still entered the editorial retry path.
4. GitHub Models cannot be treated as a guaranteed emergency provider: the live run returned HTTP 410 during a scheduled retirement brownout.
5. The existing 180-second AI evaluation wall-clock budget is necessary but insufficient as the only protection; a healthy provider could still consume the whole budget on a large candidate burst.

## Production fix

### AI evaluation cap

The scoring runtime guard now has an explicit `AI_MAX_EVALUATIONS_PER_RUN = 10` cap. The cap is independent from the 180-second wall-clock deadline and is enforced before starting each real editorial AI evaluation.

### Provider-outage fast stop

If editorial evaluation raises `AI_PROVIDERS_UNAVAILABLE`, the runtime sets a cycle-level provider halt flag. Queue precheck and new-candidate evaluation stop immediately instead of repeatedly probing known-dead providers.

### Telemetry

The runtime now emits:
- `AI_EVALUATION_START <n> ...`
- `AI_EVALUATION_LIMIT_REACHED ...`
- `AI_EVALUATION_BUDGET_EXHAUSTED ...`
- `AI_EVALUATION_HALTED provider_runtime_unavailable`
- `AI_EVALUATION_SUMMARY started <n> limit <n> provider_halted <bool>`

This makes the production bottleneck measurable rather than inferred from workflow duration.

## Gemini rate-limit evidence

The project's AI Studio screenshot for Gemini 3.1 Flash Lite shows an active project limit of 15 RPM and 250K TPM. The production publisher's 5-second inter-request throttle therefore provides a 12-RPM ceiling for its own sequential Gemini calls. The Google documentation also states that rate limits vary by model, project and tier and should be treated as project-specific rather than universal.

Official documentation: https://ai.google.dev/gemini-api/docs/rate-limits

## Batch API decision

Gemini Batch API was reviewed against the current production requirement. Google documents Batch API as asynchronous, with a target turnaround of 24 hours and suitability for non-urgent bulk processing. It is therefore **not** the primary path for live Telegram publication. It remains a candidate for offline calibration, historical rescoring and analytics workloads.

Official documentation: https://ai.google.dev/gemini-api/docs/batch-api

## Acceptance criteria for the next production cycle

The next live run must demonstrate:

1. 40-point canonical pre-AI gate remains active.
2. Candidate evaluation never exceeds 10 real editorial AI evaluations in one cycle.
3. If all providers become unavailable, the runtime stops new AI evaluations immediately.
4. No outer `timeout 240s` termination occurs.
5. Finalized items continue to be ordered by final score.
6. A successful provider evaluation produces a persisted audience score and final score.
7. The published item is the highest eligible finalized item under the canonical ordering rules.
8. `AI_EVALUATION_SUMMARY` appears in the production log.
9. State and analytics are persisted after both successful and provider-degraded cycles.

## Follow-up optimization

After this safety/performance fix is validated in production, the next optimization is a two-stage triage architecture: deterministic upper-bound pruning followed by a compact audience-only AI shortlist, with full editorial generation reserved for the small set of publication finalists. Gemini Batch API should remain an offline/background option, not a synchronous publication dependency.
