# INTILY — Queue Ordering Fix 2026-09-08

## Incident

Production observation showed that the visible `В очереди` diagnostic could disagree with the score breakdown shown for a publication, and the next publication was not guaranteed to be the highest final-score story.

## Root causes

### 1. Queue diagnostic used stale pre-AI values

The publisher initialized `remaining` from the queue before editorial AI evaluation. The diagnostic then read `importance` from that stale list. Therefore `Следующая в очереди имеет вес ...` could describe the old pre-AI score rather than the final score visible in the post.

### 2. Publication order used a different priority function

The actual publication candidate list was sorted by `publication_priority()`, which combined `editorial_value` and geographic priority. That could override the numeric score order even when the queue itself was sorted by `importance`.

### 3. Russian candidates received a random pre-AI score bonus

The legacy collector added a random `RUSSIA_WEIGHT_BONUS_MIN..MAX` value directly to `x['score']`. This meant two otherwise equivalent stories could receive different mathematical weights for geography, contradicting the canonical rule that geography is not part of relevance/scoring.

### 4. Queue capacity itself could still be geography-authoritative

The legacy `rebalance_queue()` selected Russian items up to a reserved quota before selecting WORLD items. Even with a later numeric sort, that could discard a higher-scoring WORLD story when queue capacity was tight. This was a remaining path by which geography could influence which stories survived in the durable queue.

## Correct contract

For every eligible candidate:

1. deterministic base score is recalculated without any geographic bonus;
2. AI audience-fit is evaluated before publication ordering;
3. final score is `min(100, base_score + audience_score × 3)`;
4. `importance` equals that final score for final-scored items;
5. durable queue keeps the highest qualifying stories by final score, up to `MAX_QUEUE`;
6. publication candidates are sorted by final score descending;
7. pending `pre_ai` items never outrank finalized items;
8. timestamp is used only as a tie-breaker among equivalent score stage/score;
9. geography does not override score order or queue capacity;
10. the `В очереди` diagnostic reads the same guarded queue ordering.

## Implementation — 2026-09-09 hardening

`scripts/intily_scoring_runtime_guard.py` now:

- strips the legacy random RU bonus;
- recalculates the canonical base layer;
- pre-evaluates existing pre-AI queue items through the real AI editor;
- pre-evaluates newly discovered candidates before queue admission;
- caches the generated editorial post to prevent a second AI call for the same item during publication;
- makes finalized score the sole publication priority;
- forces pending `pre_ai` items behind finalized items;
- replaces the geography-reserving legacy rebalance with a pure score-capacity rebalance;
- makes the publisher's existing `В очереди` diagnostic operate on that same guarded rebalance;
- removes stale pre-AI queue wording from generated posts;
- appends the complete score footer before image delivery.

`scripts/test_intily_scoring_runtime_guard.py` now includes an explicit regression test proving that a finalized 56-point story outranks a pending 69-point pre-AI story.

## Post integrity

The score footer is appended before image delivery. It is never truncated. If the resulting post cannot fit a Telegram photo caption, the existing image runtime must use full-text fallback rather than remove the footer or editorial tail.

## Verification status

Run #764 (`34265206024`) verified 32/32 regression tests, seven queued AI evaluations, final-score publication and `final_below_threshold=0`, but skipped discovery. Therefore it did not prove the new-search → final-score → queue reordering scenario.

The 2026-09-09 hardening is committed in `438982e9d3386f2df8eda9ba4c6666c258d5d197` and the new regression test in `fb1cda0016d53bb63bc6f0e4457e284a789857be`. A real discovery run after these commits remains the final production acceptance test.
