# INTILY Project Status — 2026-09-07

## Canonical current status

**🟡 TECHNICALLY GREEN / CMO AUDIENCE-FIT MODEL RELEASED / MEDIA RESOLUTION RELEASED / PRODUCTION VERIFICATION PENDING**

The publisher is operational and the previous v3 score-compression problem is being addressed with a two-stage editorial model. The final publication threshold remains 60. The new AI editor now evaluates target-audience fit from 1 to 10 in the same pass in which it translates and summarizes the story; this becomes an additive bonus.

## Production architecture

```text
Cloudflare schedule
  → GitHub Actions workflow_dispatch
  → scripts/intily_ai_news_runner.py
  → scripts/intily_ai_news.py
  → Telegram @intily
  → durable state + run_history in GitHub
```

## Current editorial model

### Stage 1 — deterministic materiality

- Base model: event-first scoring v3.
- Pre-AI gate: **45.0**.
- This is intentionally wider than the old 60 gate so the AI editor can distinguish professionally useful 45–59 stories from noise.

### Stage 2 — CMO / target-audience fit

The AI editor returns:

- Russian Telegram title/body/meaning;
- optional joke under existing safety/style rules;
- `audience_score` **1–10**;
- short `audience_reason`.

Target audience hypothesis:

- founders / business owners;
- executives / managers;
- product, marketing and operations specialists;
- developers / technical specialists;
- AI / technology decision-makers and advanced practitioners.

Audience bonus:

```text
1–5  → +0
6    → +3
7    → +6
8    → +9
9    → +12
10   → +15
```

Final formula:

```text
final_score = min(100, base_score + audience_bonus)
```

Final publication threshold remains **60.0**.

This is not a cosmetic score change: it separates **materiality** from **usefulness to the person we are trying to acquire and retain**.

## Production evidence before the CMO release

Run #474 (`34092034565`) was the first valid production run on scoring v2:

- 446 incoming materials;
- 403 Google News;
- 43 direct RSS;
- 443 below 60;
- 3 candidates;
- 1 new admission;
- 1 Telegram publication;
- published story score 60.1;
- VentureBeat HTTP 429.

That proved publication recovery but did not prove a healthy supply distribution. V3 was therefore not accepted as final.

## Why the model changed again

The remaining problem was not simply «find more technical news». A channel can receive hundreds of AI-related items while still having very little content worth opening for its intended professional reader.

The new model treats the target audience as a first-class editorial constraint:

```text
raw supply
  ↓
materiality
  ↓
professional audience fit
  ↓
final score
  ↓
publication
```

The AI audience score is generated during the existing translation/summarization call, so it does not add a second provider request per publication.

## Analytics release

Publisher and Production Monitor now expose audience-fit KPIs:

- number of audience evaluations;
- average audience score;
- total audience bonus;
- count/share of 8–10 scores;
- last audience score + reason + final score;
- media attempts/found/validated/photo/fallback.

New operator component:

`scripts/intily_audience_monitor.py`

New policy:

`scripts/intily_audience_policy.py`

New regression test:

`scripts/test_intily_audience_policy.py`

## Media status

Image delivery remains publisher-first and Google-News-safe:

```text
Google News wrapper
  → Google News resolver
  → real publisher URL
  → og:image / JSON-LD / image_src / Twitter / HTML candidates
  → per-candidate validation
  → Telegram sendPhoto
  → controlled text fallback
```

Google News / Google-hosted images are not accepted as successful image sources.

The code and regression coverage exist, but **live production photo delivery still requires the next scheduled cycle as proof**.

## CI

The workflow now validates:

- scoring policy;
- target-audience policy;
- Google News resolver;
- image pipeline;
- existing production analytics/policy code.

The workflow also runs the audience analytics section after each production cycle.

## Acceptance gate for this release

### Required on the next production cycle

1. CI passes on the new audience-fit code;
2. base score distribution is materially broader than the old 3/446 v2 result;
3. 45–59 items are actually entering the widened editorial pool;
4. AI returns valid `audience_score` 1–10;
5. at least one story reaches 60+ after audience bonus when fresh supply exists;
6. low-audience stories are rejected rather than published merely because they contain AI keywords;
7. Telegram publication succeeds;
8. Google News resolves to publisher URL;
9. publisher image reaches `IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT` or a precise fallback reason is recorded;
10. no Google-hosted image is accepted;
11. state and KPI analytics persist successfully.

## Documentation hierarchy

This document is the canonical current status.

Related:

- `docs/AUDIENCE_STRATEGY_2026-09-07.md`
- `docs/INTILY_ANALYTICS.md`
- `docs/INTILY_PRODUCTION_MONITORING.md`
- `docs/RELEASE_2026-09-07.md`
- `docs/SCORING_CALIBRATION_2026-09-07.md`
- `docs/IMAGE_PIPELINE_INCIDENT_2026-09-07.md`
- `docs/USER_HANDOFF.md`
- `docs/NEW_CHAT_START_PROMPT.md`
- `docs/INTILY_OPERATIONS.md`
