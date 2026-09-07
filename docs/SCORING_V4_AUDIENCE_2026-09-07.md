# INTILY — Scoring V4: Audience-Adjusted Editorial Model — 2026-09-07

## Decision

The v3 event-materiality model is retained as the deterministic base. A second CMO/editorial layer is added because **technical importance and audience value are not the same variable**.

## Two-stage formula

```text
base_score = deterministic editorial materiality
pre_gate   = 45

AI editor:
  translate + summarize + explain
  audience_score = 1..10

bonus:
  1..5  -> 0
  6     -> +3
  7     -> +6
  8     -> +9
  9     -> +12
  10    -> +15

final_score = min(100, base_score + bonus)
final_gate  = 60
```

## Why 45 is the pre-gate

The old production evidence showed severe score compression: only 3/446 materials reached 60+ under v2. Keeping 60 as both the only gate would make it impossible for the AI audience layer to contribute to selection.

45 therefore means **«worth an AI editorial look»**, not «publish».

The AI audience score then has the job of separating:

- technically interesting but professionally weak news;
- genuinely useful professional news;
- high-impact news that deserves a strong final score.

## Target reader

The current ICP hypothesis is practical AI-active professionals:

- founders / owners;
- executives / managers;
- product / marketing / operations;
- developers / technical specialists;
- AI / technology decision-makers.

The reader's expected value is:

```text
what changed → why it matters → what I can do → what risk/opportunity follows
```

## Important constraint

Audience fit cannot rescue arbitrary noise. A 1–5 audience score contributes **zero**. Even a 10/10 audience score contributes a bounded +15, so the base editorial model remains the primary quality floor.

## Runtime implementation

- `scripts/intily_audience_policy.py` — rubric and bonus curve;
- `scripts/intily_ai_news_runner.py` — production integration;
- `scripts/intily_audience_monitor.py` — historical audience KPI;
- `scripts/test_intily_audience_policy.py` — regression coverage.

The AI score is returned in the same editorial JSON call as title/body/meaning. No additional provider call is required per publication.

## Calibration policy

The first production cycles are experiments. We will monitor:

1. base score distribution;
2. audience score distribution;
3. final score distribution;
4. rejected-after-AI rate;
5. audience 8–10 share;
6. source/topic cohorts;
7. later, actual Telegram engagement when reliable telemetry exists.

The bonus curve must be changed only from observed evidence, not intuition after a single run.
