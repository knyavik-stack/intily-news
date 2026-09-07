# Intily CMO Model Review — 2026-09-07

## Decision
The scoring model is treated as an editorial growth system, not a generic AI-news classifier. The objective is to maximize the probability that the target reader opens and values a post.

## 1. Audience bonus
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

Production funnel:

`base editorial score >= 40` → AI editor → `audience_score 1–10` → linear bonus → `final score >= 60` → publish.

The AI audience score is a second editorial signal, not a replacement for materiality and evidence.

## 2. Audience expansion
The previous audience definition was too narrow and likely over-selected global enterprise/product/developer stories. Intily now targets:

1. AI-active entrepreneurs and SME owners.
2. Executives and functional managers deciding where AI can reduce cost, increase productivity, automate work or create products.
3. Product, marketing, sales, operations, HR and finance professionals using AI in daily work.
4. Developers and technical specialists.
5. AI practitioners and power users interested in tools, models, agents, workflows and implementation.
6. Russian-speaking professionals tracking Russian AI products, regulation, investment, infrastructure, education and practical adoption.

The target is defined by behavior and job-to-be-done, not job title alone.

Current evidence supports this broadening. A 2026 survey of Russian companies covers not only developers but also operations, sales, HR, marketing/support, education and finance. Sber Analytics reports AI assistants/agents being used in document processing, finance, HR, planning and customer support. Research on Russian SME owners links personal AI experience with business adoption. citeturn3search10turn3search17turn3search19

## 3. Content-interest correction
The feed now expands Russian discovery around:

- AI tools, models and agents;
- workflow automation and productivity;
- sales, marketing, customer support and HR;
- finance, accounting and operations;
- industrial AI, logistics and retail;
- medicine and education;
- cybersecurity, fraud and data risk;
- regulation and data residency;
- Russian AI companies/products and open-source ecosystem;
- infrastructure, GPUs, data centres and import substitution;
- investment/startups where there is a material consequence.

Global coverage remains important for frontier models, major platform moves, research and events that change the competitive landscape.

## 4. Geographic portfolio
Russian stories receive **no random score bonus**. Geography is a portfolio objective.

Current target hypothesis: approximately **40% Russia / 60% World**, with a tolerance band. Underrepresentation is corrected through source/query coverage and publication priority, not by falsifying relevance.

The runner now adds targeted Russian queries covering SME adoption, business functions, Russian vendors, regulation, security, infrastructure, investment and sectoral use cases.

## 5. Queue-score diagnosis
The old footer `Следующая в очереди имеет вес 58.7` was misleading. The queue is a **pre-AI editorial staging area**, so 58.7 can be a base score that has not yet received the audience evaluation.

The runtime now marks:

- `pre_ai` — deterministic/base score;
- `final` — audience score applied and final threshold checked.

The Telegram diagnostic now says `Следующая в очереди: базовый вес 58.7/100; AI-аудит ещё не проведён.` It no longer implies that 58.7 passed a 60 final gate.

A queue audit KPI separately counts pre-AI items below 60 and finalized items below 60. The invariant is: **zero finalized queue items below 60**.

## 6. Images
The image pipeline remains a production acceptance gate until a real scheduled cycle proves it. The workflow explicitly activates the hardened fetcher, and direct runner invocation now activates it through the audience-policy runtime hook as well.

Required chain:
`Google News URL → publisher URL → publisher image candidates → validation → Telegram sendPhoto`.

Google-hosted images are forbidden. Publisher Referer retry is enabled. Telegram's current `sendPhoto` API accepts uploaded photos up to 10 MB and captions up to 1024 characters after entity parsing. citeturn2search0

## 7. Production validation
The next real cycle must report:

- base-score distribution after widening the pre-AI gate;
- audience 1–10 distribution;
- audience bonus distribution;
- final-score distribution;
- AI evaluation/retry counts;
- RU/WORLD candidate and publication mix;
- queue score-stage audit;
- `IMAGE_SOURCE_RESOLVED → IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT`.

No GREEN status should be declared until the scheduled cycle demonstrates both the new editorial funnel and a real Telegram photo publication.
