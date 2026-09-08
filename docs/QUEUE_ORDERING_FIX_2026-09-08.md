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

## Correct contract

For every eligible candidate:

1. deterministic base score is recalculated without any geographic bonus;
2. AI audience-fit is evaluated before publication ordering;
3. final score is `min(100, base_score + audience_score × 3)`;
4. `importance` equals that final score for final-scored items;
5. durable queue is sorted by final score descending;
6. publication candidates are sorted by final score descending;
7. timestamp is used only as a tie-breaker;
8. geography does not override score order;
9. the `В очереди` diagnostic reads the same final-score-sorted queue.

## Implementation

`scripts/intily_scoring_runtime_guard.py` now:

- strips the legacy random RU bonus;
- recalculates the canonical base layer;
- pre-evaluates existing pre-AI queue items through the real AI editor;
- pre-evaluates newly discovered candidates before queue admission;
- caches the generated editorial post to prevent a second AI call for the same item during publication;
- forces publication priority to final `importance`;
- sorts candidates using final score, then freshness;
- preserves the existing queue/retry/deduplication mechanisms;
- appends the complete score footer before image delivery.

`scripts/test_intily_scoring_runtime_guard.py` now includes an explicit regression test that final score is the primary queue order.

## Post integrity

The score footer is appended before image delivery. It is never truncated. If the resulting post cannot fit a Telegram photo caption, the existing image runtime must use full-text fallback rather than remove the footer or editorial tail.

## Verification status

Code and regression coverage are committed. A new post-fix live production run is still required before declaring GREEN. The last observed production run (#763, before this ordering fix) passed 31 tests and published a 59-point story, but its queue had not yet been converted to final-score-first ordering.
