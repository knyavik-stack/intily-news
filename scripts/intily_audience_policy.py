"""Intily target-audience editorial policy.

Audience is a behavioral/job-to-be-done model, not a demographic claim about
current subscribers. The AI editorial pass contributes exactly 30 points of
the 100-point final score: audience_score 1–10 is mapped linearly to +3…+30.
"""

PRE_AI_THRESHOLD = 40.0
FINAL_THRESHOLD = 55.0
AUDIENCE_BONUS_MAX = 30.0

AUDIENCE_RUBRIC = {
    10: 'Immediate, material consequence: the reader should change a decision, workflow, product, spend, security posture, or operating plan now.',
    9: 'Very strong practical or strategic consequence with a clear near-term action for business, product, technology, or risk.',
    8: 'Strong concrete relevance: a material new capability, deployment, economics, competition, regulation, security event, or implementation change.',
    7: 'Useful professional context with a concrete implication or credible use case, but limited urgency or magnitude.',
    6: 'Meaningfully relevant to an AI-active professional, but the consequence is indirect, narrow, or not immediately actionable.',
    5: 'Interesting industry information; useful awareness but weak direct effect on work or decisions.',
    4: 'Mostly passive awareness; value is concentrated among specialists closely following the topic.',
    3: 'Curiosity/commentary with little practical consequence for the target reader.',
    2: 'Low-value noise, weak evidence, speculative detail, or marginal product/news information.',
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
    """Map audience score 1–10 linearly to +3…+30 (30% of 100)."""
    score = clamp_score(value)
    return round(score * 3.0, 1)


def build_evaluation_instruction():
    rubric = '\n'.join(f'{k}/10 — {v}' for k, v in AUDIENCE_RUBRIC.items())
    return (
        '\nОТДЕЛЬНАЯ ОЦЕНКА ЦЕЛЕВОЙ АУДИТОРИИ INTILY. После того как ты понял и пересказал новость, '
        'оцени её полезность именно для русскоязычного AI-активного профессионала: предпринимателя/владельца бизнеса, '
        'руководителя/менеджера, product/marketing/sales/operations/finance специалиста, разработчика/технического специалиста, '
        'AI-практика или power user. Не оценивай «насколько новость интересна вообще».\n'
        'Сначала оцени фактическое последствие: изменится ли работа, продукт, бизнес, затраты, производительность, автоматизация, '
        'технологическая стратегия, безопасность или риск; появится ли доступная возможность; нужно ли принимать решение сейчас. '
        'Учитывай как позитивные возможности, так и материальные риски, включая изменение занятости и замену отдельных задач ИИ, '
        'но не повышай оценку только из-за драматичности формулировки. Не ставь высокий балл за сам факт известного бренда, '
        'финансирования, оценки компании, слуха или прогноза без доказанного последствия.\n'
        'Шкала:\n' + rubric +
        '\nВерни дополнительно audience_score (целое число 1–10) и audience_reason (одна короткая фраза, объясняющая конкретное последствие). '
        'Это второй редакторский сигнал и ровно 30% итоговой шкалы: score × 3, то есть 1/10=+3 и 10/10=+30.\n'
    )

try:
    import intily_ai_news as _publisher
    import intily_image_pipeline as _image_pipeline
    from intily_image_runtime import fetch_image as _runtime_fetch_image

    # Finalized items below the production gate are never durable queue items.
    # Pre-AI 40–54 items remain valid queue candidates until AI editorial review.
    _original_rebalance_queue = _publisher.rebalance_queue
    def _guard_final_queue(queue, now):
        filtered = [
            item for item in (queue or [])
            if not (
                str(item.get('score_stage', 'pre_ai')) == 'final'
                and float(item.get('importance', item.get('score', 0)) or 0) < FINAL_THRESHOLD
            )
        ]
        return _original_rebalance_queue(filtered, now)
    _publisher.rebalance_queue = _guard_final_queue

    _image_pipeline.fetch_image = _runtime_fetch_image

    def _full_or_reject_photo_caption(text, limit=1024):
        sanitized = _image_pipeline._sanitize_telegram_html(text)
        if len(sanitized) > limit:
            raise ValueError('PHOTO_CAPTION_LIMIT_TEXT_FALLBACK')
        return sanitized

    _image_pipeline._photo_caption = _full_or_reject_photo_caption
    IMAGE_HARDENING_ACTIVE = True
except Exception as _image_runtime_error:
    IMAGE_HARDENING_ACTIVE = False
    IMAGE_HARDENING_ERROR = str(_image_runtime_error)[:200]
