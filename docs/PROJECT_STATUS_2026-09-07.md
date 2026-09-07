# INTILY Project Status — 2026-09-07

## Canonical current status

### Overall

**🟡 TECHNICALLY GREEN / SCORING V2 RELEASED — PRODUCTION ACCEPTANCE PENDING NEXT SCHEDULED CYCLE**

The ingestion, queue, deduplication, publication and media architecture is operational. The previous scoring calibration was rejected after production verification showed continued score compression. Scoring v2 is now the production baseline; the next Cloudflare-triggered cycle is the first valid runtime acceptance test.

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
- 60 means a concrete, materially relevant AI event; 75+ is major; 85+ is exceptional.
- Publication interval remains controlled by the existing publisher policy.
- Russia/world balancing is separate from editorial score.
- No random regional score bonus is active in the runner.

## Production evidence: run #472

Run #472 (`34091375644`) succeeded technically, but checkout log shows it ran commit `e584b0ec1775a1669c294e087c359b0e880179bc`, before scoring v2 was committed. Its useful diagnostic facts are:

- 425 incoming items;
- 423 filtered by score (99.5%);
- 2 candidates;
- both candidates were already published;
- 0 new admissions;
- score buckets: 302 / 85 / 36 / 2 / 0 / 0 / 0 / 0 for 0–39 / 40–49 / 50–59 / 60–69 / 70–79 / 80–84 / 85–89 / 90–100.

This confirms the real failure mode: the channel was not starved of source material, but the score distribution was overwhelmingly below the 60 gate. The run is **not** a v2 acceptance run.

## Scoring v2 — current production baseline

Commit: `23819a9728d225a0628f46db8dd02342fceb7997`

`scripts/intily_scoring_policy.py` is now event-first and editorial-materiality driven. The threshold remains 60; the available score is redistributed toward the properties that make a news item publishable.

| Component | Max |
|---|---:|
| AI relevance | 20 |
| AI specificity | 10 |
| Impact | 20 |
| Event concreteness | 20 |
| Practical value | 10 |
| Novelty | 4 |
| Source quality | 8 |
| Evidence | 4 |
| Freshness | 4 |
| **Total** | **100** |
| Low-signal penalty | **−6** |

### Editorial interpretation

- **<60**: weak signal, commentary, insufficiently material, or non-event content;
- **60–74**: normal publishable AI news — a concrete event with materiality;
- **75–84**: major industry event;
- **85–100**: exceptional/channel-defining event.

The model is no longer built around keyword-count accumulation. A single concrete event receives a meaningful baseline; independent impact signals then move the item toward major/exceptional tiers. Semantic story memory remains responsible for uniqueness and deduplication.

## Regression protection

The production workflow executes py_compile plus 9 unit tests before the publisher. The last verified suite passed:

- concrete AI release clears 60;
- major AI acquisition reaches 75+;
- generic AI commentary remains below 60;
- non-AI material receives zero AI relevance;
- image metadata extraction, Google News canonical resolution, candidate retry and Blockchain.News fixture all pass.

## Source health

Current runtime uses:

- CNews direct RSS;
- Euronews public `/rss` root;
- TechCult via targeted Google News `site:techcult.ru` queries;
- the established first-party/industry feeds and broad Google News discovery.

VentureBeat can still return HTTP 429 intermittently. This is an upstream source-health issue and not the publication gate itself; the broad discovery layer provides redundancy.

## Image pipeline

Resolver 2.0 is production code:

```text
Google News
  → publisher URL
  → multi-candidate metadata/JSON-LD/HTML extraction
  → per-candidate validation
  → Telegram sendPhoto
  → controlled text fallback
```

A Google News wrapper image is never accepted. Durable telemetry records attempts, found, validated, photo_sent, fallback reasons and URL provenance.

The Blockchain.News supplied publisher image is covered by a regression test. **Real production Telegram delivery has not yet been proven because run #472 published zero items.** The next successful publication is the media acceptance test.

## Release / acceptance state

- Run #471: diagnostic only; established original score compression.
- Run #472: technically SUCCESS, but pre-v2 checkout; 0 publications.
- Scoring v2: **released to `main`**.
- Documentation: `docs/SCORING_V2_RELEASE_2026-09-07.md` added.
- Next Cloudflare-triggered cycle: **first valid production acceptance run**.

### Mandatory acceptance criteria

1. workflow succeeds;
2. scoring and media unit tests pass;
3. score distribution materially expands above 60 when fresh concrete events exist;
4. at least one non-duplicate 60+ item is admitted when supply exists;
5. Telegram publication succeeds;
6. media telemetry shows `IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT`, or an explicit controlled text fallback;
7. selected image provenance points to the publisher host, never Google News.

## Documentation hierarchy

This document is the canonical current status and supersedes conflicting older status documents.

Related:

- `docs/SCORING_V2_RELEASE_2026-09-07.md`
- `docs/SCORING_CALIBRATION_2026-09-07.md`
- `docs/IMAGE_PIPELINE_INCIDENT_2026-09-07.md`
- `docs/PRODUCTION_CHANGELOG_2026-09-06_MEDIA_SOURCES.md`
- `docs/USER_HANDOFF.md`
- `docs/NEW_CHAT_START_PROMPT.md`
- `docs/INTILY_OPERATIONS.md`
