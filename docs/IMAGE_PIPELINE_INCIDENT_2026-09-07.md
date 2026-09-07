# INTILY — Image Pipeline Incident 2026-09-07

## Reported chain

The observed item was a Google News RSS URL resolving to:

`https://blockchain.news/ainews/ai-model-fatigue-hits-as-labs-escalate-releases`

The expected publisher image supplied for verification was:

`https://blockchainstock.blob.core.windows.net/features/2242046FCF14090589D5A49FFC590D13A9AF6032D71ECDBD82C9F012CD661799.jpg`

The public source page is currently indexed as “AI model fatigue hits as labs escalate releases”; the page describes rapid model launches from OpenAI, Google, Meta and Anthropic. citeturn0search0

The supplied image URL resolves to a real publisher-style 1000×524 JPG rather than a Google News placeholder. citeturn1view1

## What the pipeline now does

The resolver is publisher-first:

`Google News URL → publisher URL → metadata candidates → candidate-by-candidate download/validation → Telegram sendPhoto`

Candidate order:

1. `og:image` / `og:image:url`;
2. JSON-LD `image` / `contentUrl`;
3. `link rel=image_src`;
4. Twitter image metadata;
5. HTML `<img>` / lazy attributes / `srcset`.

A failed first candidate no longer forces text fallback; the next candidate is attempted.

Google News is explicitly forbidden as the image source. If the aggregator wrapper cannot be resolved to the publisher, the article is published text-only instead of attaching a generic Google image.

## Telemetry

Per publication the durable KPI contains:

- attempts;
- found;
- validated;
- photo_sent;
- text_fallback;
- fallback_reasons;
- selected image method;
- resolved publisher URL;
- selected image URL;
- image dimensions.

Production Monitor aggregates these metrics for 24h, 7d and stored history.

## Acceptance for this incident class

For a successful Blockchain.News-like item, production logs should show:

- `IMAGE_SOURCE_RESOLVED` with `blockchain.news` (or the actual publisher host);
- `IMAGE_FOUND`;
- `IMAGE_VALIDATED`;
- `TELEGRAM_PHOTO_SENT`;
- durable `photo_sent: 1`.

If the publisher blocks retrieval or exposes no usable image, the correct outcome is `IMAGE_FALLBACK_TEXT` plus a durable fallback reason. A generic Google News image is never an acceptable success state.

## Related source issue

The same production cycle also exposed two stale runtime direct-feed URLs: TechCult `/feed` and an obsolete Euronews MRSS path. The runtime source policy now removes the broken TechCult direct feed in favour of targeted Google News discovery and switches Euronews to its current public `/rss` root. Euronews documents its RSS/MRSS public feeds, including its news sections. citeturn2search1turn2search9
