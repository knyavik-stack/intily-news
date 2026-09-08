# INTILY — Scoring Runtime Bug / 2026-09-08

## Root cause

The deterministic base model is correctly bounded to **70 points**, and the AI audience layer is correctly designed as **+3…+30**. The missing points were not lost inside the individual weight functions.

They were lost at the **pre-AI → final score transition** in `scripts/intily_ai_news_runner.py`.

Legacy runtime logic initialized:

```python
audience_bonus = 10.0
```

before an `audience_score` existed. Therefore a story with a perfect deterministic base score of 70 received:

```text
base_score = 70
AI audience score = not evaluated
legacy default bonus = +10
observed score = 80
```

This exactly reproduces the Boss's diagnostic experiment: artificially maxing the deterministic weights produced **80 instead of 100**.

## What this proves

The missing 20 points are explained by two separate contracts being conflated:

1. **The AI layer has a maximum of +30**, but it must not be represented by a placeholder before AI evaluation.
2. The legacy placeholder **+10** was being added pre-AI, so the maximum observable pre-AI score was 70+10 = **80**.

The actual intended maximum is:

```text
Deterministic base maximum     70
AI audience maximum             30
---------------------------------
Final maximum                  100
```

No 20-point component exists independently. The apparent missing 20 came from the runtime using only a legacy +10 placeholder instead of the real AI contribution of up to +30.

## Evidence

The durable production state contained an explicit example with:

```text
base_score: 70.0
audience_score: null
audience_bonus: 10.0
final_score: 80.0
```

That is the smoking gun: the base model had already reached its full 70-point ceiling, but the runtime had injected a non-AI +10 instead of leaving the AI contribution at zero until evaluation.

## Fix

Added `scripts/intily_scoring_runtime_guard.py`.

The production workflow now runs through this guard. It intercepts the legacy runner's score function and enforces:

```text
pre-AI:  base only = 0…70
AI 1/10: base + 3
AI 10/10: base + 30
final max: 100
```

The guard also rewrites diagnostics so pre-AI items are explicitly marked `score_stage=pre_ai` and `audience_bonus=0`.

## Regression protection

Added `scripts/test_intily_scoring_runtime_guard.py` and included it in the production workflow regression gate.

The test verifies that:

- a legacy pre-AI +10 cannot survive the runtime guard;
- a perfect base score remains exactly 70 before AI evaluation;
- an evaluated AI score is allowed to contribute its real bonus;
- the complete architecture therefore has an auditable 70+30=100 maximum.

## Production acceptance

The live production cycle must still confirm:

- pre-AI max = 70;
- AI 10/10 contribution = +30;
- final max = 100;
- no phantom +10 pre-AI bonus;
- publication gate remains 55;
- score buckets reflect base scores before AI and final scores after AI.

This incident is closed at code level but remains **pending live production verification** until a new workflow run demonstrates the invariants.
