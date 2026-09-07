"""Intily target-audience policy.

This is an editorial/CMO layer, not a demographic claim about the existing
subscriber base. It is the current acquisition hypothesis for a Russian
AI-news Telegram channel and is intentionally measurable in production.

The audience is treated as practical AI-active professionals: founders and
owners, executives/managers, product/marketing/operations specialists,
developers/technical specialists, and AI/technology decision-makers.
Their core job-to-be-done is fast context: what changed, why it matters to
work/business/technology, and what action or risk follows.
"""

PRE_AI_THRESHOLD = 45.0
FINAL_THRESHOLD = 60.0
AUDIENCE_BONUS_MAX = 15.0

AUDIENCE_RUBRIC = {
    10: 'Immediate practical or strategic consequence; the reader can act, adapt a workflow, make a decision, or avoid a material risk now.',
    9: 'Very strong practical/strategic relevance with clear implications for work, product, business, technology, or risk.',
    8: 'Strong relevance; a substantial change in tools, capabilities, economics, competition, regulation, or implementation.',
    7: 'Useful professional context with a concrete implication, but not urgent or transformative.',
    6: 'Moderately useful; relevant to an AI-active professional but limited practical consequence.',
    5: 'Interesting industry information with weak or indirect practical value.',
    4: 'Mostly passive awareness; useful mainly to specialists following the topic closely.',
    3: 'Curiosity or commentary with little consequence for the target reader.',
    2: 'Low-value industry noise, weak evidence, or marginal product/news detail.',
    1: 'Essentially irrelevant to the target audience despite containing AI-related language.',
}

POSITIVE_SIGNALS = (
    'deployment', 'adoption', 'workflow', 'production', 'customer', 'revenue',
    'cost', 'roi', 'enterprise', 'business', 'developer', 'coding', 'automation',
    'productivity', 'integration', 'implementation', 'agent', 'regulation',
    'security', 'risk', 'интеграц', 'внедрен', 'бизнес', 'выручк', 'затрат',
    'окупаем', 'автоматизац', 'разработ', 'продакшн', 'практик', 'кейс',
    'безопас', 'риск', 'регулир', 'агент',
)

LOW_AUDIENCE_SIGNALS = (
    'opinion', 'prediction', 'rumor', 'rumour', 'celebrity', 'controversy',
    'мнение', 'слух', 'скандал', 'хайп', 'шумиха', 'прогноз',
)


def clamp_score(value):
    try:
        value = float(value)
    except Exception:
        raise ValueError('AUDIENCE_SCORE_INVALID')
    if value < 1 or value > 10:
        raise ValueError('AUDIENCE_SCORE_OUT_OF_RANGE')
    return round(value, 1)


def bonus_from_score(value):
    """Audience fit is a plus, not a replacement for editorial materiality.

    Scores 1–5 receive no bonus; 6–10 receive +3…+15. This prevents an
    audience score from rescuing a genuinely weak story while rewarding news
    that is materially useful to Intily's target reader.
    """
    score = clamp_score(value)
    return round(min(AUDIENCE_BONUS_MAX, max(0.0, (score - 5.0) * 3.0)), 1)


def build_evaluation_instruction():
    rubric = '\n'.join(f'{k}/10 — {v}' for k, v in AUDIENCE_RUBRIC.items())
    return (
        '\nОТДЕЛЬНАЯ ОЦЕНКА ЦЕЛЕВОЙ АУДИТОРИИ INTILY. После того как ты понял и пересказал новость, '
        'оцени её полезность именно для практического AI-профессионала: основателя/владельца бизнеса, '
        'руководителя или менеджера, product/marketing/operations специалиста, разработчика/технического специалиста '
        'или другого человека, который внедряет AI в работу. Не оценивай «насколько новость интересна вообще».\n'
        'Главные вопросы: изменит ли это работу/продукт/бизнес/технологический стек; даст ли решение, возможность, экономию, '
        'риск или важный сигнал; есть ли причина открыть пост именно сейчас.\n'
        'Шкала:\n' + rubric +
        '\nВерни дополнительно audience_score (целое число 1–10) и audience_reason (одна короткая фраза). '
        'Это не заменяет редакционный score: это отдельный audience-fit bonus.\n'
    )
