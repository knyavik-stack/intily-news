# INTILY Project Status — 2026-09-07

## Canonical current status

### Overall

**🟡 TECHNICALLY GREEN / PRODUCTION PUBLICATION RESTORED / SCORING V3 + MEDIA RESOLUTION RELEASED**

The production pipeline now successfully admits and publishes a fresh 60+ story. Run #474 is the first valid production run on the calibrated baseline. The remaining release gate is statistical validation of scoring v3 and real publisher-image delivery on the next scheduled cycle.

## Production architecture

```text
Cloudflare schedule
  → GitHub Actions workflow_dispatch
  → scripts/intily_ai_news_runner.py
  → scripts/intily_ai_news.py
  → Telegram @intily
  → durable state + run_history in GitHub
```

## Operator settings

- Editorial admission threshold: **60.0** — operator-approved and unchanged.
- 60–74.9: normal publishable AI news.
- 75–84.9: major industry event.
- 85–100: exceptional/channel-defining event.
- Publication interval remains controlled by the existing publisher policy.
- Russia/world balancing is separate from editorial score.
- No random regional score bonus is active in the runner.

## Production evidence: run #474

Run #474 (`34092034565`) checked out commit `c6a4923974e04bbc3a96f479388230a687ea2c5a` and completed successfully.

- 446 incoming materials;
- 403 from Google News;
- 43 from direct RSS;
- 443 filtered below 60;
- 3 candidates;
- 1 new admission;
- 2 candidates blocked because their keys were already published;
- 1 Telegram publication;
- published story score: **60.1**;
- queue after run: 0;
- provider: Gemini, no failover;
- source error: VentureBeat HTTP 429.

This is a material milestone: **the production publisher is no longer stuck at zero output.**

However, the distribution was still compressed: only 3/446 materials reached 60+ and none reached 70+. Therefore the v2 model is not accepted as final.

## Scoring v3 — current main

Commit: `a1cca25a3e7b1a88502556cc50bc6eede0cb74c1`

Scoring v3 replaces keyword-weight accumulation with explicit event materiality. The threshold remains 60; it is not lowered to manufacture volume.

| Component | Max |
|---|---:|
| AI relevance | 20 |
| AI specificity | 10 |
| Impact | 20 |
| Event materiality | 25 |
| Practical value | 8 |
| Novelty | 0 |
| Source quality | 7 |
| Evidence | 5 |
| Freshness | 5 |
| **Total** | **100** |
| Low-signal penalty | **−6** |

### Mathematical change

The previous model awarded points to keyword families. That created a structural problem: a real event often accumulated only a few weak signals, while an article could contain many relevant words without representing a materially important event.

V3 changes this to:

1. **AI relevance** — confirms that the story belongs in Intily;
2. **event materiality** — assigns a bounded base for a concrete launch/release/deal/funding/research/policy/incident;
3. **impact** — evaluates consequence using independent signals, major actors, risk and measurement;
4. **practical value** — evaluates actual deployment/adoption/use;
5. **source/evidence/freshness** — supporting confidence signals;
6. **semantic memory** — independently decides uniqueness.

The same keyword appearing repeatedly cannot manufacture a high score. A concrete event receives a meaningful base even when the publisher uses different wording.

Novelty is no longer part of the numeric score. A story is important because of its materiality; whether it is new to Intily is a separate deduplication problem.

## Media release

Run #474 published text because the old Google News resolution path returned `ARTICLE_SOURCE_UNRESOLVED`.

The cause is current Google News RSS behavior: wrapper URLs may return a Google shell rather than a normal HTTP redirect. A dependency-free resolver has therefore been added:

`scripts/intily_google_news.py`

It supports the current article-page decoding parameters and Google's `batchexecute` resolution path, with fail-open behavior. When successful, the publisher receives the real article URL before image extraction begins.

The image pipeline remains publisher-first and multi-candidate:

```text
Google News wrapper
  → current Google resolver
  → publisher URL
  → og:image / JSON-LD / image_src / Twitter / HTML candidates
  → per-candidate validation
  → Telegram sendPhoto
  → controlled text fallback
```

Google News and Google-hosted images are never accepted as successful photo sources.

The Blockchain.News image supplied for the incident remains an explicit regression candidate.

## CI protection

The workflow now compiles and tests:

- scoring policy;
- Google News resolver;
- image pipeline;
- existing cycle/policy code.

The next scheduled cycle is the first runtime test containing both scoring v3 and the new Google resolver.

## Source health

Current runtime uses CNews direct RSS, Euronews `/rss`, TechCult targeted Google News queries, established first-party/industry feeds and broad Google News discovery.

VentureBeat returned HTTP 429 in run #474. This is treated as a non-blocking upstream source-health issue. Repeated failures should be mitigated at source level and must not be compensated for by lowering the editorial gate.

## Release acceptance

### Already proven

- workflow executes successfully;
- production state is durable;
- publication has resumed;
- score 60+ can admit a real story;
- Telegram delivery succeeds;
- image pipeline has deterministic unit coverage.

### Next mandatory proof

1. CI passes with the new v3 + Google resolver code;
2. score distribution becomes materially healthier than the 3/446 result from v2;
3. at least one non-duplicate 60+ item is admitted when fresh supply exists;
4. Telegram publication succeeds;
5. a Google News story resolves to a publisher URL;
6. a publisher-hosted image reaches `IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT`, or a precise controlled fallback is recorded;
7. no Google-hosted image is accepted.

## Documentation hierarchy

This document is the canonical current status and supersedes conflicting older status documents.

Related current release document:

- `docs/RELEASE_2026-09-07.md`
- `docs/SCORING_V2_RELEASE_2026-09-07.md`
- `docs/SCORING_CALIBRATION_2026-09-07.md`
- `docs/IMAGE_PIPELINE_INCIDENT_2026-09-07.md`
- `docs/PRODUCTION_CHANGELOG_2026-09-06_MEDIA_SOURCES.md`
- `docs/USER_HANDOFF.md`
- `docs/NEW_CHAT_START_PROMPT.md`
- `docs/INTILY_OPERATIONS.md`
