# INTILY Production Change Log — Sources + Media — 2026-09-06/07

## Approved scope

Implemented and extended the approved media/source work:

1. add CNews, TechCult and Euronews discovery;
2. implement article-main-image attachment;
3. production verification path;
4. durable media analytics;
5. scoring calibration at the operator-approved 60 threshold;
6. regression protection and incident documentation.

## Source changes

CNews remains a direct RSS source.

TechCult's previously configured direct `/feed` endpoint returned HTTP 404 in production. Rather than keeping a permanently failing feed, TechCult is now covered by targeted Google News `site:techcult.ru` discovery queries. The public TechCult site remains active and exposes an RSS entry, but the exact direct feed endpoint could not be established reliably enough to keep the broken URL in production. citeturn3search0turn5search1

Euronews is now configured through its current public `/rss` root. Euronews documents its public MRSS/RSS feeds, including news sections. citeturn2search1turn2search9

The sources remain subject to normal scoring, AI relevance, semantic deduplication and admission gates.

## Media changes

`scripts/intily_image_pipeline.py` implements best-effort article image extraction and Telegram `sendPhoto` delivery.

Resolver 2.0:

1. resolves Google News RSS links to the publisher page via redirects;
2. if the wrapper does not redirect, attempts canonical/`og:url` publisher references;
3. refuses to use `news.google.com` as the article source;
4. parses metadata with the standard-library HTML parser, so attribute order is not significant;
5. extracts `og:image`, `og:image:url`, JSON-LD image/contentUrl, `image_src`, Twitter image, lazy HTML images and `srcset`;
6. ranks candidates by source quality and publisher-host affinity and penalizes obvious logo/placeholder/generic assets;
7. validates candidates independently and tries up to eight candidates before falling back to text.

Validation includes content type, maximum 10 MB, and minimum 200×150 dimensions. Text publication remains the safe fallback for every extraction/download/validation/upload failure.

## Real media incidents

### SecurityLab

A Google News-originated SecurityLab publication was observed with a generic Google-like image. Root cause was scraping the aggregator URL instead of the publisher page. The resolver was changed to require publisher resolution and to reject Google News as an image source.

### Tekedia

A Tekedia publication had a representative publisher image but Intily published without a photo. This exposed brittle single-candidate extraction after publisher resolution. Resolver 2.0 now tries multiple metadata/HTML candidate families independently.

### Blockchain.News

A further reported chain resolves to `blockchain.news/ainews/ai-model-fatigue-hits-as-labs-escalate-releases`, with the expected image supplied from `blockchainstock.blob.core.windows.net`. The public page is indexed with the matching title, and the supplied JPG resolves as a real 1000×524 image. citeturn0search0turn1view1

This chain is now an explicit acceptance case: production must either send the resolved publisher image or emit a controlled text fallback with a durable reason. A generic Google image is never success.

## Durable media analytics

Image telemetry is persisted in each bounded `run_history` record under `admission.image`:

- `attempts`;
- `found`;
- `validated`;
- `photo_sent`;
- `text_fallback`;
- `fallback_reasons`;
- `sources`;
- `last` provenance containing resolved publisher URL, selected image URL, extraction method, dimensions and error where applicable.

Production Monitor aggregates these metrics for 24h, 7d and stored history and reports resolution rate, Telegram photo rate, fallback rate, reasons and extraction methods.

## Scoring incident and recalibration

Production run #471 (`34090244584`) provided the decisive evidence for the scoring problem:

- 399 incoming materials;
- 393 filtered by score (98.5%);
- 6 candidates;
- 0 new admissions;
- all 6 candidates were already published;
- score distribution: 266 in 0–39, 98 in 40–49, 29 in 50–59, 6 in 60–69, and **0 above 70**.

This proves that the previous mathematical model was under-calibrated for real RSS language. The 60 threshold itself was not the root problem.

The scoring policy has now been recalibrated without lowering the gate. It uses bounded baselines and diminishing returns for AI specificity, impact, event concreteness, practical value and novelty. The intended interpretation is:

- 60–74 = strong publication candidate;
- 75–84 = major industry event;
- 85–100 = exceptional/channel-defining event.

Uniqueness is kept separate from importance: semantic story deduplication handles repeated reporting, while novelty remains only one score component.

A dedicated regression test suite now runs in CI and verifies that a concrete AI release clears 60, a major acquisition reaches high tier, generic AI commentary stays below 60, and non-AI material receives no AI relevance score.

## Production verification

Run #472 (`34090922205`) was a successful Cloudflare/GitHub cycle but started from the pre-calibration state commit `6b7fcb6`, so it is **not** evidence for the new scoring model.

The current `main` branch contains the calibrated scoring policy, repaired source configuration, scoring regression tests and CI enforcement. The next Cloudflare-triggered cycle is the first valid production acceptance run for this change set.

Acceptance criteria:

- `SCORE_BUCKETS` shows material supply at 60+ and preferably some 70+;
- qualifying 60+ material is admitted unless blocked by a genuine published/semantic-duplicate/history reason;
- an eligible queue item publishes when the Telegram interval permits;
- media KPI emits `photo_sent` or controlled `text_fallback` with a reason;
- Google News-originated media resolution points to the real publisher host.

## Current status

- Editorial threshold: **60.0**, operator-approved.
- Scoring model: recalibrated; production verification pending next cycle.
- Source expansion: CNews direct, Euronews corrected to `/rss`, TechCult moved from broken direct feed to targeted discovery.
- Image resolver 2.0: implemented and regression-tested.
- Durable photo KPI analytics: implemented.
- No scoring change is coupled to media delivery.
