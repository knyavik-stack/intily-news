# INTILY Publication Settings

**Дата актуализации:** 2026-09-08

## Effective production policy

The effective production policy is assembled by `scripts/intily_ai_news_runner.py` and the audience policy module.

| Setting | Effective value | Meaning |
|---|---:|---|
| Discovery lookback | 12 h | Maximum age eligible for discovery/queue |
| Planned search interval | 30 min | Normal discovery cadence |
| Telegram publication interval | 3 min | Minimum gap between posts |
| Pre-AI gate | **40/100** | Minimum base score to reach AI editorial/audience evaluation |
| Base score ceiling | **70/100** | Deterministic editorial layer |
| Final publication gate | **55/100** | Minimum final score after audience-fit |
| Audience score | **1–10** | AI editorial usefulness for the target audience |
| Audience bonus | **+3…+30** | `audience_score × 3`; exactly 30% of scale |
| Max queue | 20 | Durable qualifying-story capacity |
| RU/WORLD portfolio target | ~40% / ~60% | Portfolio objective; no fabricated RU content |
| Regional relevance bonus | 0 | Geography does not alter mathematical relevance |
| Joke target | 90% | Only for suitable non-serious posts; editorial gate remains independent |
| Immediate search queue threshold | 1 | Search immediately when queue has 1 or fewer stories |
| Queue diagnostics | ON | Operational observation |

## Canonical publication flow

```text
sources / discovery
    ↓
base editorial score 0–70
    ↓
pre-AI gate 40
    ↓
AI translation + summary + audience score 1–10
    ↓
audience bonus +3…+30
    ↓
final score 0–100
    ↓
final gate 55
    ↓
Telegram
```

A pre-AI 40–54 candidate is legitimate queue material. A finalized item below 55 is a reject and is removed from durable queue. It must never be published.

## Audience-fit policy

The AI score is consequence-first. High scores require concrete impact on work, product, business, economics, technology strategy, regulation, security or material risk.

The model explicitly avoids rewarding a story simply because it mentions a major AI company, a large valuation/funding round, a rumor, a forecast or a dramatic headline.

## Media policy

- Publisher-first image resolution.
- Google News is a discovery wrapper only and is never an accepted image host.
- Image candidates are validated independently so a broken or oversized first candidate does not suppress a later valid publisher image.
- **1,000,000 bytes is a hard delivery cap.** Images above 1 MB are skipped; Intily does not resize or recompress them to fit.
- If no acceptable image remains, the story may be sent text-only when the editorial/publication gate passes.
- Photo captions preserve supported Telegram HTML formatting and sanitize unsafe markup/links.
- **Photo captions are never truncated.** If the complete sanitized caption exceeds Telegram's 1024-character limit, the full text is delivered via text-only fallback so the editorial tail cannot disappear.

## Queue invariant

The durable queue may contain:

- `score_stage=pre_ai` with base 40–54;
- `score_stage=pre_ai` with base 55+;
- finalized items only when final score ≥55.

It may **not** contain `score_stage=final` with score <55. The runtime guard enforces this during queue rebalancing.

## Analytics contract

**Publisher Summary** shows only the current cycle. It reports ingestion, filtering, candidates, queue admission, publication, provider and media telemetry.

**Production Monitor** shows history over 24 hours, 7 days and stored runs. It reports publication frequency, no-publication reasons, source health, audience-fit, media delivery, provider/failover and warnings.

The analytics scripts use effective production thresholds instead of historical hard-coded 60 values.

## Last verified production evidence

Run #680 (`34219243075`) passed 21 regression tests and published one story at final score 69.1 under the old ×2 audience layer. It also exposed `final_below_threshold=4` in the queue; those were not published because the editor gate rejected them, but the queue state violated the intended invariant. The new guard closes this.

The same run hit HTTP 403 on the image path, so the new publisher-image path still needs one live confirmation after these changes.

## Operational rule

After every material change:

**verify facts → identify cause → fix → run tests → verify production result → document.**

GitHub Actions `SUCCESS` alone is not a business-result guarantee.
