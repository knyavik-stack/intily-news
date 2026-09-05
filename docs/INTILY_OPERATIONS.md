# Intily â AI News Publisher Operations

ÐÐ°ÑÐ° Ð°ÐºÑÑÐ°Ð»Ð¸Ð·Ð°ÑÐ¸Ð¸: 2026-09-02

## Production objective

Intily Ð½ÐµÐ¿ÑÐµÑÑÐ²Ð½Ð¾ Ð¾Ð±Ð½Ð°ÑÑÐ¶Ð¸Ð²Ð°ÐµÑ Ð²Ð°Ð¶Ð½ÑÐµ AI-Ð½Ð¾Ð²Ð¾ÑÑÐ¸, Ð½Ð°ÐºÐ°Ð¿Ð»Ð¸Ð²Ð°ÐµÑ Ð¸Ñ Ð² durable queue Ð¸ Ð¿ÑÐ±Ð»Ð¸ÐºÑÐµÑ Ð½Ðµ Ð±Ð¾Ð»ÐµÐµ Ð¾Ð´Ð½Ð¾Ð¹ Ð½Ð¾Ð²Ð¾ÑÑÐ¸ Ð·Ð° production cycle. Cycle Ð·Ð°Ð¿ÑÑÐºÐ°ÐµÑÑÑ ÐºÐ°Ð¶Ð´ÑÐµ 5 Ð¼Ð¸Ð½ÑÑ ÑÐµÑÐµÐ· Cloudflare Worker.

## Discovery

ÐÑÐ½Ð¾Ð²Ð½Ð¾Ð¹ discovery source â Google News RSS search. Ð¢ÐµÐºÑÑÐ¸Ðµ query-ÐºÐ»Ð°ÑÑÐµÑÑ: Ð¾Ð±ÑÐ¸Ð¹ AI, OpenAI, Anthropic/Claude, Google DeepMind/Gemini, agents/robotics, chips/Nvidia/GPU, regulation/safety/law, investment/acquisition/funding, research/breakthrough, ÑÐ¾ÑÑÐ¸Ð¹ÑÐºÐ¸Ð¹ ÐÐ, Ð¯Ð½Ð´ÐµÐºÑ/Ð¡Ð±ÐµÑ/VK Ð¸ ÑÐ¾ÑÑÐ¸Ð¹ÑÐºÐ¾Ðµ ÑÐµÐ³ÑÐ»Ð¸ÑÐ¾Ð²Ð°Ð½Ð¸Ðµ/Ð¸Ð½Ð²ÐµÑÑÐ¸ÑÐ¸Ð¸.

ÐÐ°Ð¶Ð´ÑÐ¹ Ð·Ð°Ð¿ÑÑÐº Ð¿Ð¸ÑÐµÑ Ð´Ð¸Ð°Ð³Ð½Ð¾ÑÑÐ¸ÑÐµÑÐºÐ¸Ðµ counters:

```text
RSS_QUERY ...
INGEST_SUMMARY ...
QUEUE_INGEST ...
```

Ð­ÑÐ¾ Ð¿Ð¾Ð·Ð²Ð¾Ð»ÑÐµÑ Ð¾ÑÐ»Ð¸ÑÐ¸ÑÑ Ð¾ÑÑÑÑÑÑÐ²Ð¸Ðµ Ð½Ð¾Ð²Ð¾ÑÑÐµÐ¹ Ð¾Ñ Ð¸Ñ Ð¾ÑÐ±ÑÐ°ÑÑÐ²Ð°Ð½Ð¸Ñ ÑÐ¸Ð»ÑÑÑÐ°Ð¼Ð¸.

## Freshness and memory

Discovery Ð¸ÑÐ¿Ð¾Ð»ÑÐ·ÑÐµÑ rolling lookback 12 ÑÐ°ÑÐ¾Ð². Exact RSS-item memory `known` Ð¸Ð¼ÐµÐµÑ TTL 6 ÑÐ°ÑÐ¾Ð². `known` Ð½Ðµ ÑÐ²Ð»ÑÐµÑÑÑ Ð°ÑÑÐ¸Ð²Ð¾Ð¼ Ð¿ÑÐ±Ð»Ð¸ÐºÐ°ÑÐ¸Ð¹.

ÐÐ¾Ð»Ð³Ð¾Ð²ÑÐµÐ¼ÐµÐ½Ð½Ð°Ñ Ð·Ð°ÑÐ¸ÑÐ° Ð¾Ñ Ð¿Ð¾Ð²ÑÐ¾ÑÐ¾Ð² Ð²ÑÐ¿Ð¾Ð»Ð½ÑÐµÑÑÑ ÑÐµÑÐµÐ· `published` Ð¸ semantic `stories`.

## Content quality and regional policy

Ð¦ÐµÐ»ÐµÐ²Ð¾Ð¹ ÑÐµÐ´Ð°ÐºÑÐ¸Ð¾Ð½Ð½ÑÐ¹ ÑÐ¾ÑÑÐ°Ð²: **Ð¿ÑÐ¸Ð¼ÐµÑÐ½Ð¾ 80% WORLD / 20% RUSSIA**.

Ð­ÑÐ¾ Ð½Ðµ Ð¼ÐµÑÐ°Ð½Ð¸ÑÐµÑÐºÐ°Ñ Ð±Ð»Ð¾ÐºÐ¸ÑÐ¾Ð²ÐºÐ°: ÐµÑÐ»Ð¸ Ð·Ð° Ð¿ÐµÑÐ¸Ð¾Ð´ Ð½ÐµÑ Ð´Ð¾ÑÑÐ°ÑÐ¾ÑÐ½Ð¾Ð³Ð¾ ÐºÐ¾Ð»Ð¸ÑÐµÑÑÐ²Ð° ÐºÐ°ÑÐµÑÑÐ²ÐµÐ½Ð½ÑÑ ÑÐ¾ÑÑÐ¸Ð¹ÑÐºÐ¸Ñ Ð¼Ð°ÑÐµÑÐ¸Ð°Ð»Ð¾Ð², ÑÐ²Ð¾Ð±Ð¾Ð´Ð½ÑÐµ ÑÐ»Ð¾ÑÑ Ð¿Ð¾Ð»ÑÑÐ°ÐµÑ WORLD. ÐÐ¾ Ð Ð¾ÑÑÐ¸Ñ Ð¸Ð¼ÐµÐµÑ reserved queue capacity Ð¸ publication boost, ÐºÐ¾ÑÐ¾ÑÑÐ¹ Ð¿ÑÐ¸Ð½ÑÐ´Ð¸ÑÐµÐ»ÑÐ½Ð¾ Ð²ÑÐ±Ð¸ÑÐ°ÐµÑ ÑÐ¾ÑÑÐ¸Ð¹ÑÐºÑÑ Ð¿ÑÐ±Ð»Ð¸ÐºÐ°ÑÐ¸Ñ Ð¿ÑÐ¸ Ð½ÐµÐ´Ð¾Ð±Ð¾ÑÐµ ÐºÐ²Ð¾ÑÑ, ÐµÑÐ»Ð¸ ÐµÑ ÑÐ°ÐºÑÐ¸ÑÐµÑÐºÐ°Ñ Ð´Ð¾Ð»Ñ Ð² Ð¿Ð¾ÑÐ»ÐµÐ´Ð½Ð¸Ñ Ð¿ÑÐ±Ð»Ð¸ÐºÐ°ÑÐ¸ÑÑ Ð¿Ð°Ð´Ð°ÐµÑ Ð½Ð¸Ð¶Ðµ 20%.

Ð¢ÐµÐ¼Ð°ÑÐ¸ÐºÐ° ÑÐ°ÑÑÐ¸ÑÐµÐ½Ð°: business adoption, automation, AI tools/platforms, developer/coding, cybersecurity, healthcare, education, science, industrial applications Ð¸ technology reviews.

ÐÑÐµÑÐµÐ´Ñ Ð±Ð¾Ð»ÑÑÐµ Ð½Ðµ ÑÐ²Ð»ÑÐµÑÑÑ ÑÐºÐ»Ð°Ð´Ð¾Ð¼ Ð½Ð° 100 Ð¼Ð°ÑÐµÑÐ¸Ð°Ð»Ð¾Ð². Ð Ð°Ð±Ð¾ÑÐ°Ñ ÑÐµÐ»Ñ â Ð¾ÐºÐ¾Ð»Ð¾ 36 Ð»ÑÑÑÐ¸Ñ ÑÐ²ÐµÐ¶Ð¸Ñ Ð¸ÑÑÐ¾ÑÐ¸Ð¹, hard cap â 48. ÐÑÐ¸ queue pressure Ð¿ÑÐ¸Ð¼ÐµÐ½ÑÐµÑÑÑ ranked rebalance.

## Filtering pipeline

1. RSS fetch.
2. Score.
3. Freshness.
4. Exact key dedup.
5. Semantic story dedup Ð²Ð½ÑÑÑÐ¸ discovery batch.
6. Semantic dedup Ð¿ÑÐ¾ÑÐ¸Ð² queue.
7. Semantic dedup Ð¿ÑÐ¾ÑÐ¸Ð² recent published story memory.
8. Admission Ð² durable queue.

## Durable queue

Queue ÑÑÐ°Ð½Ð¸ÑÑÑ Ð² `data/intily-ai-news-state.json` Ð¸ ÑÐ¾ÑÑÐ°Ð½ÑÐµÑÑÑ Ð² GitHub Ð¿Ð¾ÑÐ»Ðµ run.

ÐÑÐ¸ Ð¾ÑÐ¸Ð±ÐºÐµ Ð¾Ð±ÑÐ°Ð±Ð¾ÑÐºÐ¸ item Ð½Ðµ ÑÐ´Ð°Ð»ÑÐµÑÑÑ Ð¸Ð· durable queue. ÐÐ»Ñ Ð´Ð¸Ð°Ð³Ð½Ð¾ÑÑÐ¸ÐºÐ¸ ÑÐ¾ÑÑÐ°Ð½ÑÑÑÑÑ `last_failed_at`, `last_failure`, `failure_count`; cycle Ð¼Ð¾Ð¶ÐµÑ Ð¿ÑÐ¾Ð´Ð¾Ð»Ð¶Ð¸ÑÑ Ð¾Ð±ÑÐ°Ð±Ð¾ÑÐºÑ ÑÐ»ÐµÐ´ÑÑÑÐµÐ³Ð¾ item.

## Publication model

`MAX_PUBLISH = 1`. ÐÐ¾ÑÑÐ¾Ð¼Ñ Ð½Ð°ÐºÐ¾Ð¿Ð»ÐµÐ½Ð½ÑÐµ Ð½Ð¾Ð²Ð¾ÑÑÐ¸ Ð½Ðµ Ð²ÑÐ¿ÑÑÐºÐ°ÑÑÑÑ Ð¿Ð°ÑÐºÐ¾Ð¹: backlog Ð¿Ð¾ÑÑÐµÐ¿ÐµÐ½Ð½Ð¾ ÑÐ¼ÐµÐ½ÑÑÐ°ÐµÑÑÑ Ð¿Ð¾ Ð¾Ð´Ð½Ð¾Ð¹ Ð¿ÑÐ±Ð»Ð¸ÐºÐ°ÑÐ¸Ð¸ ÐºÐ°Ð¶Ð´ÑÐµ 5 Ð¼Ð¸Ð½ÑÑ.

## AI providers

Failover order: Gemini â Groq â OpenAI. Provider cooldown Ð¸ÑÐ¿Ð¾Ð»ÑÐ·ÑÐµÑÑÑ Ð´Ð»Ñ Ð½ÐµÐ´Ð¾ÑÑÑÐ¿Ð½ÑÑ Ð¿ÑÐ¾Ð²Ð°Ð¹Ð´ÐµÑÐ¾Ð².

## Editorial QA

ÐÐµÑÐµÐ´ Telegram Ð²ÑÐ¿Ð¾Ð»Ð½ÑÐµÑÑÑ editorial QA. ÐÐ°Ð½ÑÐµÐ»ÑÑÑÐºÐ¸Ðµ Ð·Ð°Ð¿ÑÐµÑÐ½ÑÐµ ÑÐ¾ÑÐ¼ÑÐ»Ð¸ÑÐ¾Ð²ÐºÐ¸ Ð¸ sensitive-topic joke suppression Ð¾ÑÑÐ°ÑÑÑÑ ÑÐ°ÑÑÑÑ ÐºÐ¾Ð½ÑÑÐ°ÐºÑÐ°.

## Runtime verification â 2026-09-01 22:40 UTC

Production run Ð¿Ð¾ÑÐ»Ðµ ingestion fix Ð´Ð°Ð»:

```text
RSS raw items: 337
score-filtered: 213
story dedup inside discovery: 32
candidates: 92
queue added: 2
already queued: 85
story queue duplicates: 2
story history duplicates: 3
published: 1
queue after: 91
heartbeat: OK
failures: 0
```

Ð­ÑÐ¾ Ð¿ÑÑÐ¼Ð¾Ðµ Ð´Ð¾ÐºÐ°Ð·Ð°ÑÐµÐ»ÑÑÑÐ²Ð¾, ÑÑÐ¾ Ð¿Ð¾Ð¸ÑÐº Ð½Ð¾Ð²Ð¾ÑÑÐµÐ¹ ÑÐ°Ð±Ð¾ÑÐ°ÐµÑ: Ð¾Ð´Ð¸Ð½ production cycle Ð¿Ð¾Ð»ÑÑÐ¸Ð» 337 RSS items Ð¸ ÑÑÐ¾ÑÐ¼Ð¸ÑÐ¾Ð²Ð°Ð» 92 ÐºÐ°Ð½Ð´Ð¸Ð´Ð°ÑÐ°.

Ð¤Ð°ÐºÑÐ¸ÑÐµÑÐºÐ¸Ð¹ state Ð¿Ð¾ÑÐ»Ðµ run: `queue=91`, `published=17`, `stories=2`, `known=94`, `health=OK`, `consecutive_failures=0`.

## Status

### GREEN

- Google News RSS discovery ÑÐµÐ°Ð»ÑÐ½Ð¾ ÑÐ°Ð±Ð¾ÑÐ°ÐµÑ.
- Ð Ð°ÑÑÐ¸ÑÐµÐ½Ð½ÑÐµ query-ÐºÐ»Ð°ÑÑÐµÑÑ ÑÐµÐ°Ð»ÑÐ½Ð¾ Ð²Ð¾Ð·Ð²ÑÐ°ÑÐ°ÑÑ Ð¼Ð°ÑÐµÑÐ¸Ð°Ð»Ñ.
- Ingestion counters ÑÐ°Ð±Ð¾ÑÐ°ÑÑ.
- Semantic story dedup ÑÐ°Ð±Ð¾ÑÐ°ÐµÑ.
- Durable queue ÑÐ¾ÑÑÐ°Ð½ÑÐµÑÑÑ.
- Failed item Ð½Ðµ Ð²ÑÐ±ÑÐ°ÑÑÐ²Ð°ÐµÑÑÑ Ð¸Ð· queue.
- Gemini ÑÑÐ¿ÐµÑÐ½Ð¾ ÑÐ³ÐµÐ½ÐµÑÐ¸ÑÐ¾Ð²Ð°Ð» Ð¼Ð°ÑÐµÑÐ¸Ð°Ð» Ð² production verification.
- Telegram delivery Ð¿Ð¾Ð´ÑÐ²ÐµÑÐ¶Ð´ÑÐ½.
- Heartbeat OK.
- Cloudflare â GitHub dispatch architecture ÑÐ°Ð±Ð¾ÑÐ°ÐµÑ.
- ÐÐ²Ð¾Ð¹Ð½Ð¾Ð³Ð¾ GitHub scheduler Ð¿Ð¾ÑÐ»Ðµ ÑÐ´Ð°Ð»ÐµÐ½Ð¸Ñ `schedule` Ð½Ðµ Ð¾Ð±Ð½Ð°ÑÑÐ¶ÐµÐ½Ð¾.

### YELLOW

- Queue `91/100`: Ð½ÑÐ¶ÐµÐ½ queue-pressure policy, ÑÑÐ¾Ð±Ñ Ð´Ð»Ð¸ÑÐµÐ»ÑÐ½ÑÐ¹ backlog Ð½Ðµ ÑÑÑÐ´ÑÐ°Ð» Ð¿ÑÐ¸Ð¾ÑÐ¸ÑÐµÑ ÑÐ²ÐµÐ¶Ð¸Ñ Ð²Ð°Ð¶Ð½ÑÑ Ð¸ÑÑÐ¾ÑÐ¸Ð¹.
- Semantic `stories=2`: Ð¸ÑÑÐ¾ÑÐ¸ÑÐµÑÐºÐ¸Ðµ Ð¿ÑÐ±Ð»Ð¸ÐºÐ°ÑÐ¸Ð¸, ÑÐ¾ÑÑÐ°Ð½ÑÐ½Ð½ÑÐµ ÑÐ°Ð½ÐµÐµ ÑÐ¾Ð»ÑÐºÐ¾ ÐºÐ°Ðº key/timestamp, Ð½ÐµÐ»ÑÐ·Ñ Ð¿Ð¾Ð»Ð½Ð¾ÑÑÑÑ Ð²Ð¾ÑÑÑÐ°Ð½Ð¾Ð²Ð¸ÑÑ Ð² semantic memory Ð±ÐµÐ· Ð²Ð½ÐµÑÐ½ÐµÐ¹ Ð¸ÑÑÐ¾ÑÐ¸Ð¸.
- GitHub Actions ÑÐ¾Ð¾Ð±ÑÐ°ÐµÑ Node 20 deprecation warning Ð´Ð»Ñ `actions/checkout@v4`; Ð½Ðµ Ð±Ð»Ð¾ÐºÐ¸ÑÑÐµÑ production, Ð½Ð¾ ÑÑÐµÐ±ÑÐµÑ Ð¿Ð»Ð°Ð½Ð¾Ð²Ð¾Ð³Ð¾ Ð¾Ð±Ð½Ð¾Ð²Ð»ÐµÐ½Ð¸Ñ.
- ÐÐ¾ÑÐ»Ðµ ÑÐ¸ÐºÑÐ° ÑÑÐµÐ±ÑÐµÑÑÑ Ð½Ð°Ð±Ð»ÑÐ´ÐµÐ½Ð¸Ðµ Ð½ÐµÑÐºÐ¾Ð»ÑÐºÐ¸Ñ Ð¿Ð¾ÑÐ»ÐµÐ´Ð¾Ð²Ð°ÑÐµÐ»ÑÐ½ÑÑ production cycles, ÑÑÐ¾Ð±Ñ Ð¿Ð¾Ð´ÑÐ²ÐµÑÐ´Ð¸ÑÑ ÑÑÐ°Ð±Ð¸Ð»ÑÐ½Ð¾Ðµ Ð¿Ð¾Ð¿Ð¾Ð»Ð½ÐµÐ½Ð¸Ðµ Ð½Ð¾Ð²ÑÐ¼Ð¸ ÑÐ¾Ð±ÑÑÐ¸ÑÐ¼Ð¸, Ð° Ð½Ðµ ÑÐ¾Ð»ÑÐºÐ¾ Ð¿ÐµÑÐµÑÐ°Ð±Ð¾ÑÐºÑ backlog.

### RED

- ÐÑÐ¸ÑÐ¸ÑÐµÑÐºÐ¸Ñ ÐºÑÐ°ÑÐ½ÑÑ Ð±Ð»Ð¾ÐºÐµÑÐ¾Ð² Ð½Ð° ÑÐµÐºÑÑÐµÐ¹ Ð¿ÑÐ¾Ð²ÐµÑÐºÐµ Ð½ÐµÑ.

## Operational rule

ÐÐ±ÑÑÐ½ÑÐ¹ production workflow Ð½Ðµ Ð·Ð°Ð¿ÑÑÐºÐ°ÐµÑÑÑ Ð²ÑÑÑÐ½ÑÑ. ÐÐ°Ð½Ð¾Ð½Ð¸ÑÐµÑÐºÐ¸Ð¹ production trigger â Cloudflare Worker. Ð ÑÑÐ½ÑÐµ/diagnostic executions Ð¸ÑÐ¿Ð¾Ð»ÑÐ·ÑÑÑÑÑ ÑÐ¾Ð»ÑÐºÐ¾ Ð´Ð»Ñ ÑÐ¾Ð³Ð»Ð°ÑÐ¾Ð²Ð°Ð½Ð½Ð¾Ð¹ Ð´Ð¸Ð°Ð³Ð½Ð¾ÑÑÐ¸ÐºÐ¸.


## Latest reliability change

2026-09-01: queue retention was separated from discovery freshness and set to 7 days. Failed items receive durable exponential retry scheduling from 5 minutes up to 6 hours.


## Quality optimization â 2026-09-02

- Freshness: **12 hours**.
- MIN_SCORE Ð¿Ð¾Ð²ÑÑÐµÐ½.
- ÐÐ¾Ð±Ð°Ð²Ð»ÐµÐ½ Ð²ÑÐ¾ÑÐ¾Ð¹ ÑÐµÐ´Ð°ÐºÑÐ¸Ð¾Ð½Ð½ÑÐ¹ gate editorial_value.
- Trusted sources Ð¿Ð¾Ð»ÑÑÐ°ÑÑ Ð¾ÑÐ´ÐµÐ»ÑÐ½ÑÐ¹ bonus.
- High-impact events Ð¿Ð¾Ð»ÑÑÐ°ÑÑ bonus.
- Applied AI / technology / tools / enterprise use cases Ð¿Ð¾Ð»ÑÑÐ°ÑÑ bonus.
- Low-signal Ð¼Ð°ÑÐµÑÐ¸Ð°Ð»Ñ Ð¿Ð¾Ð»ÑÑÐ°ÑÑ penalty.
- Semantic dedup ÑÑÐ¸Ð»ÐµÐ½ named-anchor matching Ð¸ Ð±Ð¾Ð»ÐµÐµ ÑÑÑÐ¾Ð³Ð¸Ð¼ threshold.
- Target queue: **36**.
- Hard queue cap: **48**.
- Regional target: **80% WORLD / 20% RUSSIA**.
- Russian stories Ð¸Ð¼ÐµÑÑ reserved queue capacity Ð¸ publication deficit boost.
- Queue pressure ÑÐµÑÐ°ÐµÑÑÑ ranked rebalance, Ð° Ð½Ðµ FIFO truncation.

Production metrics:

QUEUE_INGEST ... world N russia N

Ð¤Ð¸Ð½Ð°Ð»ÑÐ½ÑÐ¹ run JSON ÑÐ¾Ð´ÐµÑÐ¶Ð¸Ñ world_queue Ð¸ russia_queue.

## Latest production correction â 2026-09-02

Live state inspection found that the queue policy was working (`queue=17`, `WORLD=11`, `RUSSIA=6`, publication history `17/3`), but several legacy B-tier items with scores below the current `MIN_SCORE=9` were still present because durable queue entries were admitted under older rules and rebalance did not revalidate them.

Correction:

- every durable queue item is revalidated against the current score, AI relevance and editorial gate on every rebalance;
- stale low-score/off-topic legacy entries are removed automatically;
- an explicit AI relevance gate prevents broad Google News query leakage from unrelated technology/business stories;
- `QUEUE_REBALANCE_FILTER` exposes how many items were removed for expiry or quality.

This keeps durable memory without allowing obsolete backlog rules to contaminate current editorial output.

## Live status update â 2026-09-02

ÐÐ¾ÑÐ»Ðµ durable queue revalidation live state Ð±ÑÐ» Ð¿Ð¾Ð²ÑÐ¾ÑÐ½Ð¾ Ð¿ÑÐ¾Ð²ÐµÑÐµÐ½: queue=1, published=129, stories=114, known=61. Ð­ÑÐ¾ Ð¾Ð·Ð½Ð°ÑÐ°ÐµÑ, ÑÑÐ¾ Ð¿ÑÐµÐ¶Ð½Ð¸Ð¹ backlog Ð¾ÐºÐ¾Ð»Ð¾ 100 Ð¼Ð°ÑÐµÑÐ¸Ð°Ð»Ð¾Ð² Ð±Ð¾Ð»ÑÑÐµ Ð½Ðµ ÑÐ²Ð»ÑÐµÑÑÑ ÑÐµÐºÑÑÐ¸Ð¼ production backlog: legacy low-quality entries Ð¾ÑÐ¸ÑÐµÐ½Ñ Ð¿Ð¾ Ð´ÐµÐ¹ÑÑÐ²ÑÑÑÐµÐ¹ editorial policy.

ÐÐ´Ð¸Ð½ Ð¿Ð¾ÑÐ»ÐµÐ´ÑÑÑÐ¸Ð¹ cycle Ð·Ð°Ð²ÐµÑÑÐ¸Ð»ÑÑ Ñ FAILED_NO_PUBLISH Ð¸ consecutive_failures=1, ÑÐ¾ÑÑ ÑÐ°Ð¼ workflow Ð·Ð°Ð²ÐµÑÑÐ¸Ð»ÑÑ ÑÑÐ¿ÐµÑÐ½Ð¾ Ð¸ state Ð±ÑÐ» ÑÐ¾ÑÑÐ°Ð½ÑÐ½. ÐÑÐ¸ÑÐ¸Ð½Ð° publication-level failure Ð¾ÑÑÐ°ÑÑÑÑ Ð¿Ð¾Ð´ Ð½Ð°Ð±Ð»ÑÐ´ÐµÐ½Ð¸ÐµÐ¼ ÑÐ»ÐµÐ´ÑÑÑÐ¸Ñ Cloudflare-triggered cycles; queue Ð¸ Ð¿Ð°Ð¼ÑÑÑ Ð½Ðµ Ð¿Ð¾ÑÐµÑÑÐ½Ñ.

Ð¢Ð°ÐºÐ¶Ðµ Ð¸ÑÐ¿ÑÐ°Ð²Ð»ÐµÐ½ browser QA: focus-visible ÑÐµÐ¿ÐµÑÑ Ð¿ÑÐ¾Ð²ÐµÑÑÐµÑÑÑ ÑÐµÑÐµÐ· ÑÐµÐ°Ð»ÑÐ½ÑÑ Tab-Ð½Ð°Ð²Ð¸Ð³Ð°ÑÐ¸Ñ, Ð° Ð½Ðµ ÑÐµÑÐµÐ· programmatic focus, ÐºÐ¾ÑÐ¾ÑÑÐ¹ Ð½Ðµ Ð¾Ð±ÑÐ·Ð°Ð½ Ð°ÐºÑÐ¸Ð²Ð¸ÑÐ¾Ð²Ð°ÑÑ keyboard focus ring.

## Verification closure â 2026-09-02

Ð¡Ð»ÐµÐ´ÑÑÑÐ¸Ð¹ Cloudflare-triggered cycle Ð¿Ð¾ÑÐ»Ðµ ÐµÐ´Ð¸Ð½Ð¸ÑÐ½Ð¾Ð³Ð¾ FAILED_NO_PUBLISH Ð²Ð¾ÑÑÑÐ°Ð½Ð¾Ð²Ð¸Ð»ÑÑ ÑÑÐ°ÑÐ½Ð¾:

- RSS raw items: 169;
- candidates: 19;
- Gemini: OK;
- Editorial QA: OK;
- Telegram message_id: 138;
- published: 1;
- queue_after: 0;
- heartbeat: OK;
- consecutive failures: 0.

Ð¢Ð°ÐºÐ¸Ð¼ Ð¾Ð±ÑÐ°Ð·Ð¾Ð¼ queue-pressure correction Ð¿Ð¾Ð´ÑÐ²ÐµÑÐ¶Ð´ÑÐ½ Ð½Ðµ ÑÐ¾Ð»ÑÐºÐ¾ state inspection, Ð½Ð¾ Ð¸ Ð¿Ð¾ÑÐ»ÐµÐ´ÑÑÑÐ¸Ð¼ ÑÐµÐ°Ð»ÑÐ½ÑÐ¼ production publish. CI modernization ÑÐ°ÐºÐ¶Ðµ Ð·Ð°Ð²ÐµÑÑÑÐ½: workflows Ð¸ÑÐ¿Ð¾Ð»ÑÐ·ÑÑÑ actions/checkout@v6 Ð¸ actions/setup-node@v6, Ð° Ð¿Ð¾Ð»Ð½ÑÐ¹ Immediate QA Ñ Chromium browser gate Ð¿ÑÐ¾ÑÑÐ» SUCCESS.


## Update 2026-09-02 â 6h freshness / 60:40 regional mix / practical AI expansion

### GREEN
- Discovery window reduced from 12 hours to 6 hours.
- Editorial regional target changed to 60% WORLD / 40% RUSSIA.
- Russian query coverage expanded to support the target.
- Search coverage expanded toward AI implementation in business, practical workflows, sector adoption, technical deployment details, cost/reliability, security, incidents and operational problems.
- Editorial scoring now explicitly rewards practical implementation, risks/problems and high-exclusivity developments.
- Semantic duplicate detection was tightened: sharing a company name is no longer sufficient to classify two different events as the same story.
- Published-story memory remains durable, but semantic event suppression now uses a 24-hour horizon rather than 72 hours so legitimate follow-up developments are not blocked.
- Queue remains bounded and freshness-first; items outside the active window are intentionally dropped instead of accumulating indefinitely.

### Scheduler
- Cloudflare Worker intily-ai-news is the canonical scheduler.
- Its cron is */11 * * * *.
- Duplicate cron on intily-news-trigger is disabled.

### Queue interpretation
A queue value of zero does not mean historical memory was lost. Published and story history remain persisted separately. Queue contains only currently publishable, fresh, unique candidates. The previous zero occurred after stale queued candidates were pruned and the current candidate set was rejected by duplicate/history gates. The gates are now narrower to avoid treating unrelated stories about the same company as duplicates.


### Follow-up hardening â duplicate queue cleanup
- Added a second-pass event dedup during queue rebalance so duplicate stories restored from state or arriving through multiple search queries cannot survive as separate queue entries.
- Added title-bigram event matching to catch the same model/product launch reported with different wording.
- Added targeted Russian-source discovery queries to improve the availability of fresh Russia candidates while preserving the editorial quality gates.
- The 60/40 ratio remains a target, not fabricated content: when fewer qualifying Russian stories exist in the active 6-hour window, the system publishes fewer rather than filling the quota with irrelevant material.


---

## Current canonical status â 2026-09-02 11:25 UTC

The canonical current status is docs/PROJECT_STATUS_2026-09-02.md. Earlier sections above preserve historical recovery evidence and may contain superseded values such as 12-hour freshness, 5-minute cadence or 80/20 regional mix. Current production policy is:

- discovery freshness: **6 hours**;
- Cloudflare cadence: **every 11 minutes** (*/11 * * * *);
- regional target: **60% WORLD / 40% RUSSIA**;
- target queue: **24**; hard cap **30**;
- MIN_SCORE=9; MAX_PUBLISH=1;
- story memory: **24 hours**; known-item memory: **6 hours**.

Cloudflare cleanup completed: duplicate Worker intily-news-trigger was deleted after verification that it had no schedules and no routes. The canonical Worker is intily-ai-news.


## INTILY current publication policy — 2026-09-03

The production publisher now follows the Boss-approved publication policy from `настройки.md`. The settings are centralized at the top of `scripts/intily_ai_news.py`; every operational setting has an inline comment.

### Pipeline

1. Cloudflare Cron invokes `intily-ai-news` every 3 minutes.
2. The Worker dispatches `.github/workflows/intily-ai-news.yml` on `main`.
3. The GitHub publisher searches every 30 minutes, or immediately when the durable candidate queue has 1 or fewer stories.
4. Candidates are scored by an explainable 0–100 importance model; only `>= 60` enter memory.
5. The queue is rebuilt to at most 20 qualifying stories, reserving up to 10 RU slots so the Russian share is at least 50% when enough qualifying RU stories exist.
6. At most one story is published per cycle, with a 3-minute minimum publication interval.
7. Published history and semantic story memory are retained; only the candidate queue was reset during migration.

### Central settings

- `SEARCH_INTERVAL_SECONDS = 30 * 60` — planned search interval.
- `PUBLISH_INTERVAL_SECONDS = 3 * 60` — minimum time between publications.
- `IMPORTANCE_THRESHOLD = 60` — minimum importance score for queue/publication.
- `MAX_QUEUE = 20` — maximum candidate-memory size.
- `RUSSIA_MIN_SHARE = 0.50` — minimum RU queue share when enough qualifying RU items exist.
- `JOKE_RATE = 0.90` — target joke rate for suitable non-serious posts.
- `URGENT_SEARCH_QUEUE_THRESHOLD = 1` — immediate search threshold.

### Cache migration

The pre-change durable state contained one stale candidate, 168 published markers, 32 recent known IDs, and semantic story memory. The stale candidate queue was cleared. Published markers, known IDs, semantic story memory and publication-region history were preserved to prevent duplicate publication.

### Rollback

Before this change, the exact publisher, Cloudflare Worker version 43 source, and durable state were snapshotted under `docs/backups/2026-09-03/`. Cloudflare version history remains the infrastructure rollback point.

### Cloudflare scheduler

The active Worker remains the full existing Worker; only its scheduler cadence was changed to `*/3 * * * *`. Its four existing bindings are retained through strict inheritance.


## Canonical current state — 2026-09-04

- Russian queue target: **60%** when enough qualifying Russian candidates exist; at a full 20-item queue this is 12 RU slots.
- Importance weights now use floating-point values with **one decimal place**. Importance is recomputed on queue maintenance so freshness effects evolve with article age.
- Recency adjustment: publication age <3 hours → **+2.5** for Russia / **+1.5** for World; age >3 hours → **−2.0** for both. Exactly 3 hours receives no special recency adjustment.
- Existing Russian weighting experiment remains active: each Russian item receives a persistent random **+1.0…+5.0 percentage-point** bonus, assigned once and not rerolled during queue maintenance.
- Duplicate filtering was strengthened with canonical URL equality, exact normalized-title equality, token containment, title similarity, title n-grams, and event anchors; source name is no longer required for a duplicate.
- Cloudflare Worker scheduler is now configured for **every minute**. The Worker immediately generates an integer gate 1–3; only gate=1 dispatches GitHub. Non-selected ticks return immediately.
- GitHub workflow remains `workflow_dispatch` only; Cloudflare remains the scheduler.
- Exact pre-change backups are stored under `docs/backups/2026-09-04/`. Cloudflare pre-change Worker version 46 remains available as the infrastructure rollback point.
