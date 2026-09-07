"""Intily editorial scoring policy v3.

60 is the production publication gate. The score measures editorial
materiality, not keyword density. The model is event-first: AI relevance proves
channel fit; an explicit event family supplies the main base score; consequence,
actor scale, measurable effect, source quality and freshness refine it.

Uniqueness is intentionally outside the score. Semantic story memory decides
whether an event is new, so an important event is not made less important just
because several publishers reported it.
"""

from datetime import datetime, timezone

THRESHOLD = 60.0

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


def _event_concreteness(blob, title):
    """Return a materiality base for a concrete event, not keyword density."""
    hits = [name for name, terms in EVENT_FAMILIES.items() if any(term in blob for term in terms)]
    if not hits:
        return 0.0

    primary = {
        'launch': 17.0,
        'release': 17.0,
        'deal': 19.0,
        'money': 17.0,
        'research': 16.0,
        'policy': 18.0,
        'incident': 18.0,
    }
    value = max(primary[name] for name in hits)

    # A second independent event family is evidence of a richer story, but is capped.
    value += min(4.0, max(0, len(hits) - 1) * 2.0)
    if any(actor in blob for actor in MAJOR_ACTORS):
        value += 2.0
    if any(signal in blob for signal in MAJOR_EVENT_SIGNALS):
        value += 2.0
    if any(ch.isdigit() for ch in title):
        value += 1.0
    return min(WEIGHTS['event_concreteness'], value)


def _ai_specificity(blob, ai_terms):
    hits = _distinct_hits(blob, ai_terms)
    if not hits:
        return 0.0
    return min(WEIGHTS['ai_specificity'], 4.0 + max(0, hits - 1) * 1.25)


def _impact(blob, high_impact_terms, risk_terms):
    """Estimate consequence using independent signals and diminishing returns."""
    impact_hits = _distinct_hits(blob, high_impact_terms)
    risk_hits = _distinct_hits(blob, risk_terms)
    actor = any(term in blob for term in MAJOR_ACTORS)
    major_signal = any(term in blob for term in MAJOR_EVENT_SIGNALS)
    measured = any(term in blob for term in MEASUREMENT_SIGNALS)

    if not impact_hits and not risk_hits:
        return 0.0

    value = 5.0
    value += min(5.0, max(0, impact_hits - 1) * 1.5)
    value += min(5.0, risk_hits * 2.5)
    if actor:
        value += 2.0
    if major_signal:
        value += 2.0
    if measured:
        value += 1.0
    return min(WEIGHTS['impact'], value)


def _practical(blob):
    hits = _distinct_hits(blob, PRACTICAL_SIGNALS)
    if not hits:
        return 0.0
    return min(WEIGHTS['practical_value'], 2.0 + max(0, hits - 1) * 1.25)


def _source_quality(source, quality_trusted, trusted):
    source = source.strip().lower()
    if source in quality_trusted:
        return WEIGHTS['source_quality']
    if source in trusted:
        return 5.0
    return 3.0


def _evidence(desc):
    length = len(' '.join(str(desc or '').split()))
    if length < 50:
        return 0.5
    if length < 140:
        return round(0.5 + (length - 50) / 90.0 * 1.5, 1)
    if length < 320:
        return round(2.0 + (length - 140) / 180.0 * 3.0, 1)
    return 5.0


def score_components(x, ai_relevant, high_impact_terms, application_terms,
                     practical_terms, risk_terms, exclusivity_terms,
                     quality_trusted, trusted, low_signal_terms):
    blob = _blob(x)
    title = str(x.get('title', '') or '').strip().lower()
    source = str(x.get('source', '') or '').strip().lower()

    relevance = WEIGHTS['relevance'] if ai_relevant(x) else 0.0
    ai_terms = tuple(set(high_impact_terms) | set(application_terms) | set(practical_terms) | set(risk_terms) | set(exclusivity_terms))
    parts = {
        'relevance': relevance,
        'ai_specificity': _ai_specificity(blob, ai_terms),
        'impact': _impact(blob, high_impact_terms, risk_terms),
        'event_concreteness': _event_concreteness(blob, title),
        'practical_value': _practical(blob),
        'novelty': 0.0,
        'source_quality': _source_quality(source, quality_trusted, trusted),
        'evidence': _evidence(x.get('desc', '')),
        'freshness': _freshness(_age_hours(x)),
    }
    penalty_terms = low_signal_terms or LOW_SIGNAL_DEFAULTS
    parts['low_signal_penalty'] = 6.0 if _distinct_hits(blob, penalty_terms) else 0.0
    return {k: round(v, 1) for k, v in parts.items()}


def calculate(x, ai_relevant, high_impact_terms, application_terms,
              practical_terms, risk_terms, exclusivity_terms,
              quality_trusted, trusted, low_signal_terms):
    parts = score_components(
        x, ai_relevant, high_impact_terms, application_terms,
        practical_terms, risk_terms, exclusivity_terms,
        quality_trusted, trusted, low_signal_terms,
    )
    total = sum(parts[k] for k in WEIGHTS) - parts['low_signal_penalty']
    return round(_clamp(total), 1), parts


def tier(score):
    if score >= 85.0:
        return 'S'
    if score >= THRESHOLD:
        return 'A'
    return 'B'
