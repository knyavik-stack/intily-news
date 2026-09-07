# Production Changelog — 2026-09-07 — CMO Model V2

## Changes shipped

### Audience scoring
- AI editor score remains 1–10.
- Bonus changed from the old nonlinear `0…+15` model to strict linear `+2…+20`.
- 1/10 = +2, 2/10 = +4, …, 10/10 = +20.
- Pre-AI gate widened from 45 to 40.
- Final publication gate remains 60.

### Target audience
Expanded from a narrow enterprise/product/developer hypothesis to a behavior-based Russian-speaking AI-active audience: entrepreneurs/SME owners, managers, product, marketing, sales, operations, HR, finance, developers, AI practitioners and power users.

### Russian content
- Publication portfolio target changed to approximately 40% Russia / 60% World.
- No random Russian score bonus.
- Added targeted Russian discovery queries for SME adoption, functions, vendors, regulation, security, infrastructure, investment and sectoral AI use.

### Queue diagnostics
- Explicit `pre_ai` vs `final` score stage.
- `58.7` in queue is now described as a base/pre-AI score rather than a final publication score.
- Queue score audit distinguishes pre-AI values below 60 from finalized values below 60.
- Finalized queue items below 60 are an invariant violation.

### Media
- Hardened publisher image fetch remains active in CI and direct runner execution.
- Google-hosted images are forbidden.
- Publisher Referer retry is enabled.
- Acceptance remains a real Telegram `sendPhoto` event, not a unit-test result.

## Why
The previous model optimized technical news relevance instead of attention/value for the intended reader. The current design treats Intily as an editorial product whose KPI is target-audience utility.

## Acceptance gate
The next scheduled production cycle must demonstrate:
1. wider pre-AI candidate pool;
2. meaningful 1–10 audience score distribution;
3. linear bonus distribution;
4. final scores and publications driven by audience fit;
5. materially healthier RU/WORLD portfolio;
6. zero finalized queue items below 60;
7. real publisher image resolution and Telegram photo delivery.
