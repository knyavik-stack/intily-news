# Intily scoring v2 — release note (2026-09-07)

## Why v1 was rejected

Production run #472 completed successfully but did not provide evidence that the 60-point gate was calibrated correctly. The previous model still distributed too much of the score across weak keyword-derived dimensions, so a genuinely concrete AI event could remain below the publication gate.

The production requirement is unchanged: **60/100 remains the publication threshold**. We are changing the meaning of the score rather than lowering the gate.

## v2 model

The score is now event-first and editorial-materiality driven:

| Dimension | Weight |
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

### Interpretation

- **<60** — do not publish: mention, commentary, weak signal, or insufficiently material event.
- **60–74** — publishable AI news: concrete event with clear materiality.
- **75–84** — major industry event.
- **85–100** — exceptional/channel-defining event.

A single real event (launch, release, acquisition, funding, material research result, regulation, security incident, etc.) now receives a substantial event baseline. Impact then separates ordinary events from consequential ones. Keyword repetition cannot manufacture importance.

Uniqueness remains the responsibility of semantic story memory/deduplication and is not confused with importance.

## Regression coverage

Existing `scripts/test_intily_scoring_policy.py` remains the contract:

1. concrete OpenAI release clears 60;
2. major AI acquisition reaches 75+;
3. generic AI commentary stays below 60;
4. non-AI story receives zero relevance and remains below the gate.

The production workflow runs these tests before publisher execution.

## Release status

Commit: `23819a9728d225a0628f46db8dd02342fceb7997`

This commit is the new production scoring baseline. The next Cloudflare-triggered production run is the acceptance run for v2. It must report score buckets and demonstrate that concrete fresh AI events can cross 60 while generic commentary remains below it.

## Acceptance criteria

- workflow succeeds;
- score policy tests pass;
- no regression in durable deduplication;
- at least one fresh qualifying AI event reaches the 60 gate when supply exists;
- publication is successful;
- image pipeline reports `IMAGE_FOUND` → `IMAGE_VALIDATED` → `TELEGRAM_PHOTO_SENT` for the selected article, or an explicit controlled text fallback;
- no Google News image is ever accepted as a publication image source.
