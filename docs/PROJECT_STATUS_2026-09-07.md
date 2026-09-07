# INTILY Project Status — 2026-09-07

## Canonical current status

**🟡 98% PRODUCTION-CODE READY / LIVE MEDIA VERIFICATION PENDING**

The publisher architecture, two-stage editorial model, Russian audience expansion, publisher-first media resolver, image normalization and strict 1 MB delivery policy are implemented. CI and the latest scheduled production cycle are green. The remaining verification gate is proving that a fresh qualifying article produces a real Telegram photo through the complete production path.

## Latest production verification

- Run **#505** completed successfully on 2026-09-07.
- Media runtime installation passed.
- All policy/image regression tests passed.
- News engine completed successfully.
- Analytics and state persistence completed successfully.
- This run was very short and did not provide a qualifying fresh publication, so it is evidence of **CI/runtime health**, not proof of successful Telegram photo delivery.

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

## Media policy — hardened 2026-09-07

The image path now treats image retrieval as a separate production subsystem. Google News is discovery transport only and can never be an accepted image source.

```text
Google News discovery URL
  → publisher URL resolution
  → multi-strategy image discovery
  → candidate-by-candidate validation
  → publisher Referer retry
  → Google-hosted image rejection
  → bounded source download (8 MiB)
  → local format normalization
  → resize/compression
  → STRICT delivery payload <= 1,000,000 bytes
  → sendPhoto
  → text fallback with explicit reason
```

### Hard image limits

- **Intily delivery payload: maximum 1,000,000 bytes (1 MB decimal).**
- The 8 MiB source limit is an internal fetch ceiling only; a source image is never delivered at that size.
- Non-JPEG sources are normalized to JPEG before delivery.
- Images larger than 1 MB are resized/compressed until they fit the hard cap.
- Minimum output dimensions remain 200×150.
- Google News / Google-hosted image URLs are never accepted as successful media.
- Candidate discovery was expanded to include `og:image`, secure/article image metadata, JSON-LD, `image_src`, Twitter metadata, lazy/data image attributes, `srcset`, `<source>` and CSS URL candidates.
- WebP dimension validation now falls back to Pillow when a low-level WebP header is not one of the explicitly parsed variants.

## Production incident found and corrected

Run **#503** failed before the publisher started because an image-pipeline regression test was coupled to an internal candidate-method label. That test was corrected to assert the actual fallback-image invariant. Run **#505** subsequently passed the complete CI/test stage and production engine.

A second compatibility issue introduced during the 1 MB/source-limit hardening was also corrected: the hardening module now exposes a backward-compatible source-fetch alias while the delivery runtime retains the strict 1 MB payload cap.

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

Production monitoring records:

- deterministic score buckets;
- audience score distribution 1–10;
- average audience score;
- total and average audience bonus;
- 8–10 audience-fit share;
- pre-AI queue items below final threshold;
- final queue items below 60 — mandatory invariant = 0;
- RU/WORLD publication portfolio;
- image attempts/found/validated/photo/fallback;
- image source, dimensions, source payload size, final payload size and failure reason.

## Current acceptance gate

To move from **98%** to **GREEN / production-verified**, the next qualifying production cycle must demonstrate:

1. CI passes, including the new image runtime tests;
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

- `docs/CMO_MODEL_REVIEW_2026-09-07.md`
- `docs/INTILY_ANALYTICS.md`
- `docs/INTILY_PRODUCTION_MONITORING.md`
- `docs/RELEASE_2026-09-07.md`
- `docs/SCORING_CALIBRATION_2026-09-07.md`
- `docs/IMAGE_PIPELINE_INCIDENT_2026-09-07.md`
- `docs/USER_HANDOFF.md`
- `docs/NEW_CHAT_START_PROMPT.md`
- `docs/INTILY_OPERATIONS.md`
