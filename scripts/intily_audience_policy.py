"""Intily target-audience editorial policy.

Audience is a behavioral/job-to-be-done model, not a demographic claim about
current subscribers. The score is produced by the same AI editorial pass that
translates and summarizes the story.
"""

PRE_AI_THRESHOLD = 40.0
FINAL_THRESHOLD = 55.0
AUDIENCE_BONUS_MAX = 20.0

AUDIENCE_RUBRIC = {
    10: 'Immediate practical or strategic consequence; the reader can act, change a workflow, make a decision, or avoid a material risk now.',
    9: 'Very strong practical/strategic relevance with clear implications for work, product, business, technology, or risk.',
    8: 'Strong relevance; a substantial change in tools, capabilities, economics, competition, regulation, or implementation.',
    7: 'Useful professional context with a concrete implication, but not urgent or transformative.',
    6: 'Moderately useful; relevant to an AI-active professional with a meaningful but limited consequence.',
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
    'безопас', 'риск', 'регулир', 'агент', 'российск', 'рунет', 'импортозамещ',
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
    """Map audience score 1–10 linearly to +2…+20."""
    score = clamp_score(value)
    return round(score * 2.0, 1)


def build_evaluation_instruction():
    rubric = '\n'.join(f'{k}/10 — {v}' for k, v in AUDIENCE_RUBRIC.items())
    return (
        '\nОТДЕЛЬНАЯ ОЦЕНКА ЦЕЛЕВОЙ АУДИТОРИИ INTILY. После того как ты понял и пересказал новость, '
        'оцени её полезность именно для русскоязычного AI-активного профессионала. Это может быть предприниматель или '
        'владелец малого/среднего бизнеса, руководитель/менеджер, product/marketing/sales/operations/finance специалист, '
        'разработчик/технический специалист, AI-практик или power user. Не оценивай «насколько новость интересна вообще».\n'
        'Главные вопросы: изменит ли это работу, продукт, бизнес, затраты, производительность, автоматизацию, технологии '
        'или риск; даст ли инструмент/решение/возможность; важно ли знать это сейчас; применимо ли это в российском '
        'контексте или помогает понимать мировой AI-рынок. На сколько это вредит конечному человеку, в период потери рабочих мест и замены людей на ИИ\n'
        'Шкала:\n' + rubric +
        '\nВерни дополнительно audience_score (целое число 5–10) и audience_reason (одна короткая фраза). '
        'Это второй редакторский сигнал. Его вклад в итоговый score линейный: score × 2, то есть 1/10=+2 и 10/10=+20.\n'
    )

# Runtime activation: direct runner invocation uses the same hardened image
# fetch and the strict <=1 MiB Telegram payload as production CI.
try:
    import intily_image_pipeline as _image_pipeline
    from intily_image_runtime import fetch_image as _runtime_fetch_image
    _image_pipeline.fetch_image = _runtime_fetch_image
    IMAGE_HARDENING_ACTIVE = True
except Exception as _image_runtime_error:
    IMAGE_HARDENING_ACTIVE = False
    IMAGE_HARDENING_ERROR = str(_image_runtime_error)[:200]
