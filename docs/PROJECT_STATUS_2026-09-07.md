# INTILY Project Status — 2026-09-07

## Canonical current status

**🟡 98% PRODUCTION-CODE READY / LIVE MEDIA VERIFICATION PENDING**

The publisher architecture, two-stage editorial model, Russian audience expansion, publisher-first media resolver, and strict 1 MB media acceptance policy are implemented. The last scheduled production cycle was green. The latest media hard-reject code change is now committed; its CI verification and a fresh qualifying Telegram photo are the remaining evidence gates.

## Important media decision

**1 MB is a hard reject, not a compression target.** If the selected source image is larger than **1,000,000 bytes (1 MB decimal)**, Intily must skip that image. It must not resize or compress it merely to make it fit. The story may continue as text-only if the editorial/publication gates pass.

```text
candidate image
  → download
  → payload > 1,000,000 bytes? → REJECT / IMAGE_TOO_LARGE
  → otherwise → validate → sendPhoto
```

The internal source-fetch ceiling may be higher than 1 MB because it is only a guard against excessive downloads; it is never a delivery limit and never means an oversized image should be transformed for delivery.

## Latest production verification

- Run **#577** completed successfully on 2026-09-07 at 16:51 UTC.
- Media runtime installation passed.
- Policy/image regression tests passed on that run.
- News engine, analytics and state persistence completed successfully.
- Run #577 predates the final hard-reject commit, so it does not prove the new media policy.
- The current code change is committed as `19248a29d8393bb4fe6b1400ae49bfcd7cd4b9da`; the matching runtime regression tests are committed as `b15e67be3317141dd701cbe48eefbdd81067a83e`.

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

## Russian content strategy

The target portfolio remains approximately **40% RUSSIA / 60% WORLD**. It is a portfolio objective, not a hard relevance override.

The system does **not** manufacture Russian content to satisfy the ratio: if there are fewer qualifying Russian stories in the active window, WORLD fills the available slot.

## Analytics

Production monitoring records deterministic score buckets, audience score distribution, audience bonus, queue threshold invariants, RU/WORLD portfolio, and image attempts/found/validated/photo/fallback telemetry including image source, dimensions, source payload size, final payload size and failure reason.

## Current acceptance gate

To move from **98%** to **GREEN / production-verified**, the next qualifying production cycle must demonstrate:

1. CI passes, including image runtime tests;
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
12. any source image above 1 MB is rejected rather than compressed/resized;
13. no Google-hosted image is accepted;
14. RU/WORLD portfolio behavior remains within the target policy when qualifying supply exists;
15. durable state and KPI telemetry persist successfully.

## Documentation hierarchy

This document is the canonical current status.

Related:

- `docs/CMO_MODEL_REVIEW_2026-09-07.md`
- `docs/INTILY_ANALYTICS.md`
- `docs/INTILY_PRODUCTION_MONITORING.md`
- `docs/RELEASE_2026-09-07.md`
- `docs/SCORING_CALIBRATION_2026-09-07.md`
- `docs/IMAGE_PIPELINE_INCIDENT_2026-09-07.md`
- `docs/PRODUCTION_CHANGELOG_2026-09-07_MEDIA_1MB.md`
- `docs/USER_HANDOFF.md`
- `docs/NEW_CHAT_START_PROMPT.md`
- `docs/INTILY_OPERATIONS.md`
