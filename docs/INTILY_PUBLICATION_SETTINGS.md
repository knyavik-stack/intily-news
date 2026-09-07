# INTILY Publication Settings

**Дата актуализации:** 2026-09-07

## Effective production policy

The effective production policy is assembled by `scripts/intily_ai_news_runner.py` on top of the base engine. The runner values below therefore override older base-file defaults where they differ.

| Setting | Effective value | Meaning |
|---|---:|---|
| Discovery lookback | 12 h | Maximum age eligible for discovery/queue |
| Planned search interval | 30 min | Normal discovery cadence |
| Telegram publication interval | 3 min | Minimum gap between posts |
| Pre-AI gate | 40/100 | Minimum base score to reach AI editorial/audience evaluation |
| Final publication gate | **55/100** | Minimum final score after audience-fit |
| Audience score | 1–10 | AI editorial usefulness for the target audience |
| Audience bonus | +2…+20 | `audience_score × 2` |
| Max queue | 20 | Durable qualifying-story capacity |
| RU/WORLD portfolio target | ~40% / ~60% | Portfolio objective; no fabricated RU content |
| Regional relevance bonus | 0 | Geography does not alter mathematical relevance |
| Joke target | 90% | Only for suitable non-serious posts; editorial gate remains independent |
| Immediate search queue threshold | 1 | Search immediately when queue has 1 or fewer stories |
| Queue diagnostics | ON | Temporary footer for operational observation |

## Canonical publication flow

```text
sources / discovery
    ↓
base score
    ↓
pre-AI gate 40
    ↓
AI translation + summary + audience score 1–10
    ↓
audience bonus +2…+20
    ↓
final score
    ↓
final gate 55
    ↓
Telegram
```

The 55 threshold is an editorial admission threshold, not a request to publish weak news. The audience layer can raise a professionally useful 40–54 base candidate, while the final gate still rejects material below 55.

## Media policy

- Publisher-first image resolution.
- Google News is a discovery wrapper only and is never an accepted image host.
- Image candidates are validated independently so a broken or oversized first candidate does not suppress a later valid publisher image.
- **1,000,000 bytes is a hard delivery cap.** Images above 1 MB are skipped; Intily does not resize or recompress them to fit.
- If no acceptable image remains, the story may be sent text-only when the editorial/publication gate passes.
- Photo captions preserve supported Telegram HTML formatting, sanitize unsafe markup/links, and are bounded to Telegram's 1024-character caption limit after escaping.

## Analytics contract

**Publisher Summary** shows only the current cycle. It reports current ingestion, filtering, candidates, queue admission, publication, provider and media telemetry.

**Production Monitor** shows history over 24 hours, 7 days and stored runs. It reports publication frequency, no-publication reasons, source health, audience-fit, media delivery, provider/failover and warnings.

The analytics scripts import the effective editorial thresholds rather than duplicating hard-coded historical values.

## Production observations

### Run #577 — 2026-09-07

Run #577 was technically successful but lasted about **3m53s** from runner start to cleanup. The news engine itself did not spend that time on RSS search: it logged `SEARCH_SKIPPED`, then spent the majority of the runtime in AI editorial retries/failover.

Observed provider conditions:

- Gemini first recovered after a retry, then later hit repeated 503/timeout conditions;
- Groq returned HTTP 403 / error 1010 and was circuit-opened;
- OpenAI returned HTTP 429 / no credits and was circuit-opened;
- the queue contained existing items, so the run still attempted editorial processing and retried failed items.

This explains the near-four-minute runtime. It is a provider-availability/retry-budget issue, not an RSS collection loop. The system correctly avoided publishing when all attempted items failed editorial QA.

### Run #578 — 2026-09-07

Run #578 completed successfully in roughly **28 seconds**. It demonstrated that a publisher-hosted image can be found and validated: the selected image was **48,472 bytes**. It was not sent as a photo because the old caption-length guard emitted `CAPTION_TOO_LONG`.

The guard is now replaced by a safe Telegram-HTML caption path. The previous implementation also stripped all formatting tags from photo captions; that regression is fixed so bold/italic/link/code formatting is retained while unsafe markup is removed.

### Run #579 — 2026-09-07

Run #579 failed fast in the regression gate, before the news engine, because the caption test exposed a post-escaping length bug. The fix now bounds the final sanitized Telegram HTML rather than raw pre-escaped text.

### Post-#579 media fix

The media pipeline now enforces the 1 MB limit while iterating candidates, so an oversized first image is rejected immediately and the resolver continues to the next candidate. A second runtime-side 1 MB defense remains in place.

The next scheduled production cycle must verify the complete path:

`IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT`

with formatted caption preserved and sent image payload ≤1,000,000 bytes.

## Operational rule

After every material change:

**verify facts → identify cause → fix → run tests → verify production result → document.**

GitHub Actions `SUCCESS` alone is not a business-result guarantee.
