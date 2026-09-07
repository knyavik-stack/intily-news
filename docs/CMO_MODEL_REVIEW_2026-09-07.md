# Intily CMO Model Review — 2026-09-07

## Decision
The scoring model is treated as an editorial growth system, not a generic AI-news classifier.

### Audience bonus
AI editor audience-fit is 1–10 and maps linearly to +2…+20:
- 1 → +2
- 2 → +4
- 3 → +6
- 4 → +8
- 5 → +10
- 6 → +12
- 7 → +14
- 8 → +16
- 9 → +18
- 10 → +20

This bonus is intentionally positive even at 1/10 because the AI editor's score is a second editorial signal, not a hard gate. The base editorial model remains responsible for materiality and evidence.

## Audience expansion hypothesis
The previous audience definition was too narrow and likely over-selected global enterprise/product/developer stories. Intily's target audience is broadened to include:

1. AI-active entrepreneurs and SME owners.
2. Executives and functional managers deciding where AI can reduce cost, increase productivity, automate work or create new products.
3. Product, marketing, sales, operations and finance professionals using AI in daily work.
4. Developers and technical specialists.
5. AI practitioners and power users who want concrete tools, model releases, agents, workflows and implementation patterns.
6. Russian-speaking professionals tracking the Russian AI market, local products, regulation, investment, infrastructure, education and practical adoption.

The target is therefore defined by behavior and job-to-be-done, not by job title alone.

## Content-interest correction
The feed should balance:
- global AI model/tool/agent/platform releases;
- practical workflows and implementation;
- AI business economics, productivity and automation;
- Russian AI products, companies, investments and adoption;
- regulation, security and major incidents;
- research when it changes capabilities or practice;
- notable creator/developer ecosystems when there is concrete utility.

Low-value celebrity, generic opinion, speculative hype and repetitive funding coverage remain deprioritized unless there is a clear consequence for the target reader.

## Geographic policy
Russian stories should not receive a random score bonus. Geographic balance is a separate editorial portfolio objective.

The production system should monitor the rolling RU/WORLD mix and detect underrepresentation rather than distort relevance scoring. Source/query expansion is the preferred correction mechanism.

## Queue-score bug diagnosis
The displayed message `Следующая в очереди имеет вес 58.7` is not evidence that the 60 threshold is working incorrectly by itself. The queue can contain a candidate admitted under an earlier/pre-final scoring stage or a pre-existing queued item whose score was calculated before the final gate. However, a production invariant is required: **no item may enter the publish queue with final score < FINAL_THRESHOLD**.

Implement explicit queue audit telemetry:
- `queue_admitted_score_min/max`;
- `queue_below_final_threshold_count`;
- `queue_score_stage`;
- `final_score_at_admission`.

If a queue item is below 60, it must be re-evaluated/re-scored before publication or removed from the publish queue. The publisher's "next in queue" status must use the same final score field that governs admission.

## Images
The image pipeline remains a production blocker until a real scheduled cycle demonstrates publisher resolution + validated image + Telegram photo. Do not mark GREEN based on unit tests alone.

Required telemetry chain:
`IMAGE_SOURCE_RESOLVED → IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT`.

Google News-hosted images are never acceptable.

## Next experiment
The next production cycle is the validation experiment for this model. We need actual distribution data before further numerical tuning. The key metrics are audience score distribution, bonus distribution, final-score distribution, RU/WORLD mix, queue invariant violations and image success rate.
