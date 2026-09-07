"""Intily editorial scoring policy v3.

55 is the production publication gate after the separate audience-fit layer.
The score measures editorial materiality, not keyword density. The model is
event-first: AI relevance proves channel fit; an explicit event family supplies
the main base score; consequence, actor scale, measurable effect, source quality
and freshness refine it.

Uniqueness is intentionally outside the score. Semantic story memory decides
whether an event is new, so an important event is not made less important just
because several publishers reported it.
"""

from datetime import datetime, timezone

THRESHOLD = 55.0

# Interface-compatible component names. The maxima sum to exactly 100.
WEIGHTS = {
    'relevance': 20.0,
    'ai_specificity': 10.0,
    'impact': 20.0,
    'event_concreteness': 25.0,
    'practical_value': 8.0,
    'novelty': 0.0,
    'source_quality': 7.0,
    'evidence': 5.0,
    'freshness': 5.0,
}

EVENT_FAMILIES = {
    'launch': ('launch', 'launched', 'debut', 'unveils', 'unveiled', 'запуст', 'старт'),
    'release': ('release', 'released', 'version', 'rollout', 'available', 'релиз', 'выпуст', 'обновлен', 'представ'),
    'deal': ('acquisition', 'acquired', 'merger', 'partnership', 'agreement', 'поглощ', 'приобр', 'слиян', 'партнёр', 'партнер', 'соглашен', 'сделк'),
    'money': ('funding', 'investment', 'invested', 'financing', 'revenue', 'billion', 'million', 'финансир', 'инвестиц', 'выручк', 'миллиард', 'млн'),
    'research': ('study', 'research', 'paper', 'experiment', 'trial', 'findings', 'исследован', 'эксперимент', 'испытан', 'отчёт', 'отчет'),
    'policy': ('regulation', 'regulations', 'law', 'approved', 'regulator', 'policy', 'регулир', 'закон', 'одобр', 'регулятор'),
    'incident': ('breach', 'outage', 'incident', 'vulnerability', 'exploit', 'attack', 'утеч', 'сбой', 'инцидент', 'уязвим', 'эксплойт', 'атак'),
}

MAJOR_ACTORS = (
    'openai', 'anthropic', 'google', 'deepmind', 'microsoft', 'meta', 'nvidia',
    'apple', 'amazon', 'xai', 'mistral', 'alibaba', 'baidu', 'sber', 'сбер',
    'yandex', 'яндекс', 'vk', 'росатом',
)

MAJOR_EVENT_SIGNALS = (
    'flagship', 'frontier', 'state-of-the-art', 'breakthrough', 'record',
    'largest', 'first-ever', 'worldwide', 'global', 'national', 'critical',
    'впервые', 'прорыв', 'рекорд', 'крупнейш', 'миров', 'национальн', 'критическ',
)

MEASUREMENT_SIGNALS = (
    'benchmark', 'accuracy', 'performance', 'latency', 'cost', 'revenue', 'users',
    'employees', 'customers', 'percent', '%', 'billion', 'million',
    'бенчмарк', 'точност', 'производительност', 'задержк', 'стоимост', 'выручк',
    'пользовател', 'клиент', 'сотрудник', 'процент', 'миллиард', 'млн',
)

PRACTICAL_SIGNALS = (
    'deployment', 'adoption', 'implementation', 'workflow', 'customer', 'revenue',
    'cost', 'roi', 'integration', 'production', 'developer', 'coding', 'automation',
    'внедрен', 'кейс', 'выручк', 'затрат', 'окупаем', 'процесс', 'операц',
    'интеграц', 'продакшн', 'разработ', 'программ', 'автоматизац',
)

LOW_SIGNAL_DEFAULTS = {
    'opinion', 'sponsored', 'advertisement', 'coupon', 'horoscope', 'giveaway',
    'stocks', 'stock price', 'мнение читателей', 'реклама', 'промокод', 'гороскоп'
}


def _blob(x):
    return (str(x.get('title', '')) + ' ' + str(x.get('desc', '')) + ' ' + str(x.get('source', ''))).lower()


def _distinct_hits(blob, terms):
    return len({term for term in terms if term in blob})


def _clamp(value, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(value)))


def _age_hours(x):
    try:
        return max(0.0, (datetime.now(timezone.utc).timestamp() - float(x.get('time', 0) or 0)) / 3600.0)
    except Exception:
        return 24.0


def _freshness(age_hours):
    if age_hours <= 1.0:
        return 5.0
    if age_hours <= 3.0:
        return 4.0
    if age_hours <= 6.0:
        return 3.0
    if age_hours <= 12.0:
        return 1.0
    return 0.0
