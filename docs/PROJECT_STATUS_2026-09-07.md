# INTILY Project Status — 2026-09-07

## Canonical current status

**🟡 98% PRODUCTION-CODE READY / LIVE VERIFICATION PENDING**

The publisher architecture, two-stage editorial model, Russian audience expansion, media resolver and strict image payload policy are implemented. The remaining gate is live production verification after the latest CI/media changes.

## Production architecture

```text
Cloudflare schedule
  → GitHub Actions workflow_dispatch
  → scripts/intily_ai_news_runner.py
  → scripts/intily_ai_news.py
  → Telegram @intily
  → durable state + run_history in GitHub
```

## Editorial model

### Stage 1 — deterministic materiality

- Event-first scoring v3.
- Pre-AI gate: **40.0**.
- This is deliberately wider than the final publication gate so the AI editor can evaluate professionally useful borderline stories.

### Stage 2 — CMO / target-audience fit

The same AI editorial pass returns:

- Russian Telegram title/body/meaning;
- optional joke under existing safety/style rules;
- `audience_score` **1–10**;
- short `audience_reason`.

Target audience hypothesis:

- founders / business owners;
- executives / managers;
- product, marketing, sales, operations and finance specialists;
- developers / technical specialists;
- AI / technology decision-makers and advanced practitioners.

Audience bonus is strictly linear:

```text
1  → +2
2  → +4
3  → +6
4  → +8
5  → +10
6  → +12
7  → +14
8  → +16
9  → +18
10 → +20
```

Final formula:

```text
final_score = min(100, base_score + audience_score * 2)
```

Final publication threshold remains **60.0**.

The queue can therefore contain a pre-AI item below 60. That is intentional: the item has only passed the **40.0 pre-AI gate**. It must not be described to readers as having a final weight of 58.7. The runner rewrites that diagnostic to explicitly say that the AI audit has not yet been performed.

## Media policy — corrected 2026-09-07

The previous image path had two independent weaknesses: publisher resolution could fall back to an unresolved Google News wrapper, and the implementation used Telegram's much larger API upload limit as the local payload limit.

The production path is now:

```text
Google News discovery URL
  → Google News publisher resolver
  → real publisher URL
  → og:image / JSON-LD / image_src / Twitter / HTML candidates
  → publisher Referer retry
  → Google-hosted image rejection
  → source fetch up to bounded 8 MiB
  → local normalization/compression
  → STRICT Telegram payload <= 1,000,000 bytes
  → sendPhoto
  → text fallback with explicit reason
```

### Hard image limits

- **Telegram payload maximum for Intily: 1,000,000 bytes (1 MB decimal).**
- Source download is separately bounded at 8 MiB only to permit safe local optimization of a legitimate publisher image.
- Oversized publisher images are not sent as-is: they are resized/compressed to JPEG until the 1 MB cap is met.
- Minimum output dimensions remain 200×150.
- Google News / Google-hosted image URLs are never accepted as successful media.

New runtime:

`scripts/intily_image_runtime.py`

New regression suite:

`scripts/test_intily_image_runtime.py`

The workflow installs a pinned major-version range of Pillow and executes the new tests before production.

## Production incident found and corrected

The latest verified production run before the media-runtime release was **Run #503**. It failed before the publisher started because an existing image-pipeline regression test expected the method label `twitter_image`, while the actual valid fallback image was correctly reached. The run therefore published nothing; this was a CI test failure, not a Telegram/media runtime failure.

The test was corrected to assert the actual production invariant — the valid fallback URL and dimensions — instead of coupling the test to an internal candidate-method label.

## Previous production evidence

Run #474 was the first valid production run on scoring v2:

- 446 incoming materials;
- 403 Google News;
- 43 direct RSS;
- 443 below 60;
- 3 candidates;
- 1 new admission;
- 1 Telegram publication;
- published story score 60.1;
- VentureBeat HTTP 429.

The subsequent CMO model was introduced because this distribution was still too compressed.

The pre-release production telemetry also demonstrated that the audience model itself was being evaluated: the monitor recorded 9 audience evaluations with average 8.0 and average bonus +9.0, and the last-20 portfolio was RU=9 / WORLD=11 (45% RU). This is encouraging but is not a substitute for post-release verification.

## Russian content strategy

The target portfolio remains approximately **40% RUSSIA / 60% WORLD**. It is a portfolio objective, not a hard relevance override.

Russian discovery has been expanded across:

- business adoption and automation;
- SME productivity;
- Russian AI models and agents;
- Yandex, Sber, VK, MTS, MegaFon, Ozon, Avito;
- finance and banking;
- industry, logistics and retail;
- medicine, education, HR and legal use cases;
- cybersecurity and fraud;
- regulation and personal data;
- investment and startups;
- robotics, computer vision and infrastructure;
- RBC, Kommersant, VC.ru and TASS targeted discovery;
- CNews direct RSS.

The system does **not** manufacture Russian content to satisfy the ratio: if there are fewer qualifying Russian stories in the active window, WORLD fills the available slot.

## Analytics

Production monitoring now records:

- deterministic score buckets;
- audience score distribution 1–10;
- average audience score;
- total and average audience bonus;
- 8–10 audience-fit share;
- pre-AI queue items below final threshold;
- final queue items below 60 — mandatory invariant = 0;
- RU/WORLD publication portfolio;
- image attempts/found/validated/photo/fallback;
- image source, dimensions and failure reason.

## Current acceptance gate

To move from **98%** to **GREEN / production-verified**, the next Cloudflare-triggered production cycle must demonstrate:

1. CI passes, including the new 1 MB image runtime tests;
2. fresh discovery produces a non-empty candidate pool;
3. 40–59 pre-AI stories can enter the editorial pool;
4. AI returns valid audience scores 1–10;
5. audience bonuses are exactly +2…+20 according to the score;
6. at least one fresh story reaches 60+ after audience evaluation;
7. no finalized queue item remains below 60;
8. Telegram publication succeeds;
9. Google News resolves to the publisher URL when the source is a Google wrapper;
10. a real publisher image reaches `IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT`;
11. the sent payload is **<=1,000,000 bytes**;
12. no Google-hosted image is accepted;
13. RU/WORLD portfolio behavior remains within the target policy when qualifying supply exists;
14. durable state and KPI telemetry persist successfully.

## Documentation hierarchy

This document is the canonical current status.

Related:

- `docs/AUDIENCE_STRATEGY_2026-09-07.md`
- `docs/CMO_MODEL_REVIEW_2026-09-07.md`
- `docs/INTILY_ANALYTICS.md`
- `docs/INTILY_PRODUCTION_MONITORING.md`
- `docs/RELEASE_2026-09-07.md`
- `docs/SCORING_CALIBRATION_2026-09-07.md`
- `docs/IMAGE_PIPELINE_INCIDENT_2026-09-07.md`
- `docs/USER_HANDOFF.md`
- `docs/NEW_CHAT_START_PROMPT.md`
- `docs/INTILY_OPERATIONS.md`
