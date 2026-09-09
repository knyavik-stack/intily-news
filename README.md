# INTILY — Telegram AI News Automation

INTILY is the dedicated Telegram AI news publication subsystem.

## Current production status

**🟡 PRODUCTION VERIFICATION MODE** — scoring/queue ordering has been hardened so final score is authoritative; the next real discovery cycle must still verify the new-search → final-score → queue → publication path end-to-end.

Production flow:

1. Cloudflare `intily-ai-news` runs the minute scheduler.
2. The scheduler dispatches GitHub Actions according to the production cadence.
3. GitHub Actions runs the Python publisher.
4. The publisher discovers, ranks, deduplicates, queues and publishes to Telegram.
5. Publisher state is persisted to `data/intily-ai-news-state.json`.

## Current editorial contract

- Pre-AI gate: **40/100**.
- Base deterministic model: **0–70**.
- AI audience-fit: **1–10 → +3…+30**.
- AI layer: exactly **30% of the 100-point scale**.
- Final formula: `min(100, base_score + audience_score × 3)`.
- Final publication gate: **55/100**.
- A finalized item below 55 is rejected and removed from durable queue.
- Pre-AI 40–54 remains valid until AI editorial evaluation.
- Finalized items are ordered by final score; geography is not a mathematical score bonus and cannot displace a higher-scoring story from queue capacity.

## Media contract

- Publisher-first image resolution.
- Google News is discovery transport only; Google-hosted images are forbidden.
- **1,000,000 bytes is a hard image limit**; no resize/recompress.
- Broken/oversized candidates are skipped and the next candidate is attempted.
- Telegram HTML formatting is preserved and unsafe markup is sanitized.
- Photo captions are **never truncated**. If the full sanitized caption exceeds Telegram's 1024-character caption limit, the full text is sent through text-only fallback.

## Canonical documentation

- `docs/PROJECT_STATUS_2026-09-09.md` — canonical current status.
- `docs/PROJECT_STATUS_2026-09-08.md` — previous status snapshot.
- `docs/QUEUE_ORDERING_FIX_2026-09-08.md` — original queue-ordering incident analysis.
- `docs/SCORING_CALIBRATION_2026-09-08.md` — canonical scoring model and acceptance criteria.
- `docs/INTILY_ANALYTICS.md` — current analytics contract.
- `docs/INTILY_PUBLICATION_SETTINGS.md` — effective production settings.
- `docs/INTILY_PRODUCTION_MONITORING.md` — monitoring and incident interpretation.
- `docs/INTILY_OPERATIONS.md` — operational reference.
- `docs/USER_HANDOFF.md` — handoff instructions.
- `docs/NEW_CHAT_START_PROMPT.md` — context recovery for a new chat.

## Verification status

Run #764 (`34265206024`) successfully executed 32/32 regression tests, evaluated seven queued items with AI and published a final-score-ranked 64-point story. It did not run discovery, so the new-search reordering scenario was not proven. The latest guard/test changes are now committed; the next discovery run is the required production acceptance test.

## Security

This repository is public. Secret values must never be committed or printed to logs. Runtime secrets are stored in GitHub/Cloudflare secret stores.
