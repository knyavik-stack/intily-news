# INTILY Source Expansion — 2026-09-06

## Approved sources

The production discovery layer now adds these direct sources at runtime:

- CNews — `https://www.cnews.ru/` — RUSSIA
- TechCult — `https://techcult.ru/` — RUSSIA
- Euronews — `https://euronews.com/` — WORLD

They are intentionally added as independent direct feeds, not as extra Google News queries.

## Why direct sources

Google News is the broad discovery layer. Direct feeds provide source-level resilience and allow us to measure whether a publisher contributes genuinely new stories rather than only duplicates already present in the aggregator.

## Runtime sources

Configured feed endpoints:

- CNews: `https://www.cnews.ru/inc/rss/news.xml`
- TechCult: `https://techcult.ru/feed`
- Euronews: `https://www.euronews.com/rss?format=mrss&level=theme&name=next`

The first production cycle after deployment is the authoritative test of feed compatibility. Search-engine inspection confirms CNews and TechCult expose RSS functionality on their sites; the actual workflow must still report HTTP/XML success and item yield before the source is considered healthy.

## Editorial handling

The three sources do not bypass the normal pipeline:

`direct RSS → score → AI relevance → quality → semantic dedup → admission → queue → publication`

CNews and TechCult are treated as trusted/quality sources for scoring. Euronews is trusted but is not allowed to compensate for weak content by itself.

## Required analytics

For each source we need:

- raw items;
- source errors;
- score buckets;
- candidates after quality/dedup;
- duplicate overlap;
- new queue admissions;
- publications.

The key metric is **unique incremental supply**, not raw RSS volume.

## Decision rule for future source expansion

Do not keep adding sources merely because they return many items. A source earns continued priority when it contributes fresh, relevant stories that are not already covered by Google News and existing direct feeds.
