# INTILY Project Status — 2026-09-07

## Canonical current status

### Overall

**🟡 TECHNICALLY GREEN / EDITORIAL SUPPLY RECALIBRATION IN PRODUCTION VERIFICATION**

The production architecture works. The current blocker was identified as a scoring-distribution problem, not a lack of incoming news.

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

- Editorial admission threshold: **60.0** — operator-approved.
- Publication interval: controlled by existing publisher policy.
- Russia/world balancing is separate from editorial score.
- No random regional score bonus is active.

## Root-cause finding: zero publications

Production run #471 (`34090244584`) produced:

- 399 incoming items;
- 393 filtered by score (98.5%);
- 6 candidates;
- 0 new admissions;
- all 6 candidates were already published;
- score buckets: 266 / 98 / 29 / 6 / 0 / 0 / 0 / 0 for 0–39 / 40–49 / 50–59 / 60–69 / 70–79 / 80–84 / 85–89 / 90–100.

Therefore the statement “all news was already published” is false as a general explanation. Most material never reached admission because the score model compressed real-world stories below 60. The six remaining candidates were indeed already published.

## Scoring model — current

`scripts/intily_scoring_policy.py` remains deterministic and sums to 100 before the low-signal penalty:

| Component | Max |
|---|---:|
| AI relevance | 25 |
| AI specificity | 10 |
| Impact | 15 |
| Event concreteness | 10 |
| Practical value | 10 |
| Novelty | 8 |
| Source quality | 8 |
| Evidence | 4 |
| Freshness | 5 |
| Timeliness | 5 |
| Low-signal penalty | −6 |

The previous implementation relied too heavily on raw keyword-hit counts. The current model uses bounded baselines and diminishing returns so a real event receives a meaningful base score while keyword repetition cannot inflate it.

### Editorial interpretation

- 0–39: weak signal / mention;
- 40–49: relevant but ordinary;
- 50–59: meaningful but not strong enough;
- **60–74: strong publication candidate**;
- 75–84: major industry event;
- 85–100: exceptional/channel-defining event.

Importance and uniqueness are intentionally separate. Semantic deduplication determines whether an event is new; novelty contributes only part of its importance score.

## Scoring regression protection

Added `scripts/test_intily_scoring_policy.py` and included it in the production workflow. CI now checks:

- concrete AI release clears 60;
- major AI acquisition reaches high tier;
- generic AI commentary stays below 60;
- non-AI material does not gain AI relevance.

## Source health corrections

Production run #471 also found stale direct-feed endpoints:

- TechCult `/feed` → HTTP 404;
- old Euronews MRSS path → HTTP 404;
- VentureBeat → HTTP 429.

Current runtime policy:

- CNews remains direct RSS;
- Euronews uses its public `/rss` root;
- TechCult is covered by targeted Google News `site:techcult.ru` queries instead of a broken direct endpoint.

## Image pipeline

Resolver 2.0 is implemented:

```text
Google News
  → real publisher URL
  → metadata/JSON-LD/HTML candidate set
  → per-candidate validation
  → Telegram sendPhoto
  → controlled text fallback
```

Google News can never be accepted as the image source.

Durable media analytics are stored in `run_history.admission.image` and aggregated by `scripts/intily_monitor.py` for 24h/7d/history:

- attempts;
- found;
- validated;
- photo_sent;
- text fallback;
- fallback reasons;
- extraction sources;
- selected/resolved URL provenance.

Reported real incidents covered SecurityLab, Tekedia and Blockchain.News. The latter's supplied image is a real publisher-hosted JPG and is now an explicit acceptance case.

## Production verification state

- Run #471: **valid diagnostic evidence**, pre-recalibration.
- Run #472 (`34090922205`): SUCCESS but used pre-calibration state commit, therefore **not accepted as scoring verification**.
- Current `main`: calibrated scoring + source corrections + scoring tests + media pipeline.
- Next Cloudflare-triggered cycle: **first valid production acceptance run**.

### Acceptance

A successful next cycle should demonstrate:

1. non-zero 60+ score supply;
2. preferably non-zero 70+ supply;
3. at least one 60+ candidate admitted when not a true duplicate/history hit;
4. publication when interval permits;
5. media telemetry showing `photo_sent` or controlled fallback;
6. Google News media resolution pointing to the publisher host.

## Documentation hierarchy

For current work, this document supersedes older 2026-09-06 status statements where they conflict with the current state.

Related current docs:

- `docs/SCORING_CALIBRATION_2026-09-07.md`
- `docs/IMAGE_PIPELINE_INCIDENT_2026-09-07.md`
- `docs/PRODUCTION_CHANGELOG_2026-09-06_MEDIA_SOURCES.md`
- `docs/USER_HANDOFF.md`
- `docs/NEW_CHAT_START_PROMPT.md`
- `docs/INTILY_OPERATIONS.md`
