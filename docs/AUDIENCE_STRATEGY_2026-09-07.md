# INTILY — Target Audience & CMO Editorial Strategy — 2026-09-07

## 1. Strategic correction

Intily must not optimize for «AI news» as a technical category. It must optimize for **news that is worth interrupting the target reader for**.

The current model therefore has two independent questions:

1. **Is this materially important AI news?** — deterministic editorial score.
2. **Is this useful to the person we want to attract and retain?** — AI editorial audience-fit score.

The second score is produced by the same AI pass that translates and summarizes the story, so it evaluates the final human-readable understanding rather than only the RSS headline.

## 2. Target audience hypothesis

This is an explicit acquisition hypothesis, not a claim about current subscribers.

### Core ICP

Russian-speaking, professionally active people who use or evaluate AI in real work:

- founders / business owners;
- executives and managers;
- product, marketing and operations specialists;
- developers and technical specialists;
- AI / technology decision-makers and advanced practitioners.

### Their job-to-be-done

They do not need another stream of everything that happened in AI. They need fast answers to:

- **Что изменилось?**
- **Почему это важно мне/моей компании/моей работе?**
- **Что я могу сделать с этим?**
- **Какой риск или возможность появился?**

This is consistent with current news-consumption research: audiences increasingly value efficient summaries and contextualization, while professional AI content demand is shifting toward practical questions and implementation rather than abstract hype. citeturn0search10turn0search17

## 3. What belongs in Intily

High audience-fit stories tend to involve:

- a material change in AI products/models/agents;
- enterprise adoption and real deployments;
- measurable productivity, cost, revenue or capability changes;
- AI infrastructure/economics that affect implementation;
- regulation, safety or security with real consequences;
- important research with a credible path to use;
- major deals, funding or strategic moves that change competition;
- practical tools/workflows that can materially change how the reader works.

## 4. What should usually lose

- generic «AI is changing the world» commentary;
- minor feature updates without meaningful consequence;
- hype and predictions without evidence;
- celebrity/company drama unrelated to technology or business impact;
- benchmark trivia without a decision or practical implication;
- repeated reports of an already-known event.

## 5. Audience score

The AI editor returns `audience_score` from **1 to 10** and a short `audience_reason` in the same JSON response as the Russian post.

| Score | Meaning |
|---:|---|
| 10 | Immediate action/decision/risk/opportunity |
| 8–9 | Strong practical or strategic consequence |
| 6–7 | Useful professional context |
| 5 | Interesting but weak practical value |
| 1–4 | Mostly noise/curiosity/passive awareness |

### Bonus

Audience fit is deliberately an **additive bonus**, not a replacement for materiality:

```text
1–5  → +0
6    → +3
7    → +6
8    → +9
9    → +12
10   → +15
```

Final score:

```text
final_score = min(100, base_editorial_score + audience_bonus)
```

Publication gate remains **60**.

The deterministic pre-AI gate is **45**. This widens the editorial supply enough to let the audience layer rescue a genuinely useful story that was too weak under keyword/event-only scoring, while preventing low-signal material from entering the AI/editorial path indiscriminately.

## 6. Why this is better than simply lowering the threshold

Lowering the final threshold would publish weaker stories. The two-stage model instead separates:

- materiality;
- audience usefulness;
- duplication;
- freshness;
- final publication eligibility.

A 45-point materiality signal is not automatically publishable. It must still demonstrate audience value in the actual editorial pass and reach 60 after the bonus.

## 7. Measurement loop

Production analytics now records:

- number of audience evaluations;
- average audience score observed in the cycle/history;
- total audience bonus;
- count/share of 8–10 scores;
- final score after audience bonus;
- audience reason for the latest evaluated item.

The first production cycles are calibration data. We should not freeze the ICP or bonus curve permanently until enough real observations accumulate.

## 8. External evidence used for the hypothesis

- Reuters Institute reports that audiences value summaries, translations and recommendations as efficient forms of AI-enabled news personalization. citeturn0search10
- Reuters Institute's 2026 research shows AI-chatbot news use is growing but remains a minority behavior; this supports keeping the product useful as a direct, concise news destination rather than assuming everyone wants an AI interface. citeturn0search14
- Current B2B content-demand research reports growing AI consumption among directors, C-level leaders and managers, with stronger demand for practical questions such as agents, copilots and immediate business use. citeturn0search17
- A 2025 study of B2B Telegram users reported frequent daily Telegram use and strong demand for news/professional/applied content, supporting Telegram as a relevant distribution environment for the hypothesis. citeturn0search2

These sources are external market evidence; they are **not** direct measurements of Intily subscribers.

## 9. Future CMO loop

Once Telegram engagement data is reliably available, audience-fit should be recalibrated against actual outcomes:

```text
AI audience score
  → publication
  → views / forwards / reactions / saves (when reliable)
  → topic + source + format cohorts
  → calibration of audience rubric and bonus
```

Until those downstream metrics are available, no engagement outcome is invented.
