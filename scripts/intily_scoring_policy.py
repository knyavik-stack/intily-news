"""Intily editorial scoring policy v4.

The production score is split into two independent editorial layers:
- base editorial model: 0–70 points, deterministic and event/consequence-first;
- AI audience-fit: 1–10 mapped to 3–30 points, exactly 30% of the 100-point scale.

The model is deliberately not keyword-count scoring. A concrete material event
can score highly even when the source uses different wording, while commentary,
speculation and weakly evidenced stories stay below the gate.
"""

from datetime import datetime, timezone

THRESHOLD = 55.0
BASE_MAX = 70.0
AI_MAX = 30.0

# IMPORTANT: these are point allocations, not multipliers. Their sum MUST equal
# BASE_MAX. Every component function below is also bounded by its allocation.
WEIGHTS = {
    'relevance': 12.0,
    'ai_specificity': 6.0,
    'impact': 16.0,
    'event_concreteness': 18.0,
    'practical_value': 8.0,
    'novelty': 0.0,
    'source_quality': 5.0,
    'evidence': 3.0,
    'freshness': 2.0,
}

if round(sum(WEIGHTS.values()), 6) != BASE_MAX:
    raise RuntimeError('Scoring weight contract broken: WEIGHTS must sum to BASE_MAX')

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
        return WEIGHTS['freshness']
    if age_hours <= 3.0:
        return 1.5
    if age_hours <= 6.0:
        return 1.0
    if age_hours <= 12.0:
        return 0.5
    return 0.0


def _event_concreteness(blob, title):
    """Score verifiable event materiality, not the number of matching words."""
    hits = [name for name, terms in EVENT_FAMILIES.items() if any(term in blob for term in terms)]
    if not hits:
        return 0.0
    primary = {
        'launch': 13.0, 'release': 13.0, 'deal': 14.0, 'money': 11.0,
        'research': 11.0, 'policy': 14.0, 'incident': 14.0,
    }
    value = max(primary[name] for name in hits)
    value += min(2.0, max(0, len(hits) - 1) * 1.0)
    if any(actor in blob for actor in MAJOR_ACTORS):
        value += 6.0
    if any(signal in blob for signal in MAJOR_EVENT_SIGNALS):
        value += 6.0
    if any(ch.isdigit() for ch in title):
        value += 0.5
    return min(WEIGHTS['event_concreteness'], value)


def _ai_specificity(blob, ai_terms):
    hits = _distinct_hits(blob, ai_terms)
    if not hits:
        return 0.0
    return min(WEIGHTS['ai_specificity'], 2.5 + max(0, hits - 1) * 0.8)


def _impact(blob, high_impact_terms, risk_terms):
    """Estimate consequence with independent scale, risk and measurable-effect signals."""
    impact_hits = _distinct_hits(blob, high_impact_terms)
    risk_hits = _distinct_hits(blob, risk_terms)
    actor = any(term in blob for term in MAJOR_ACTORS)
    major_signal = any(term in blob for term in MAJOR_EVENT_SIGNALS)
    measured = any(term in blob for term in MEASUREMENT_SIGNALS)
    if not impact_hits and not risk_hits:
        return 0.0
    value = 4.0
    value += min(4.0, max(0, impact_hits - 1) * 1.25)
    value += min(4.0, risk_hits * 2.0)
    if actor:
        value += 6.5
    if major_signal:
        value += 6.5
    if measured:
        value += 6.0
    return min(WEIGHTS['impact'], value)


def _practical(blob):
    hits = _distinct_hits(blob, PRACTICAL_SIGNALS)
    if not hits:
        return 0.0
    return min(WEIGHTS['practical_value'], 2.0 + max(0, hits - 1) * 1.0)


def _source_quality(source, quality_trusted, trusted):
    source = source.strip().lower()
    if source in quality_trusted:
        return WEIGHTS['source_quality']
    if source in trusted:
        return min(3.5, WEIGHTS['source_quality'])
    return min(2.0, WEIGHTS['source_quality'])


def _evidence(desc):
    length = len(' '.join(str(desc or '').split()))
    if length < 50:
        return 0.3
    if length < 140:
        return round(0.3 + (length - 50) / 90.0 * 0.7, 1)
    if length < 320:
        return round(1.0 + (length - 140) / 180.0 * 2.0, 1)
    return 3.0


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
    parts['low_signal_penalty'] = 6.0 if _distinct_hits(blob, low_signal_terms or LOW_SIGNAL_DEFAULTS) else 0.0
    return {k: round(v, 1) for k, v in parts.items()}


def calculate(x, ai_relevant, high_impact_terms, application_terms,
              practical_terms, risk_terms, exclusivity_terms,
              quality_trusted, trusted, low_signal_terms):
    parts = score_components(
        x, ai_relevant, high_impact_terms, application_terms,
        practical_terms, risk_terms, exclusivity_terms,
        quality_trusted, trusted, low_signal_terms,
    )
    base_total = sum(parts[k] for k in WEIGHTS) - parts['low_signal_penalty']
    # Keep the deterministic layer on an explicit 70-point ceiling. This is
    # a safety invariant: AI audience-fit owns the remaining 30 points.
    total = _clamp(base_total, 0.0, BASE_MAX)
    return round(total, 1), parts


def tier(score):
    if score >= 85.0:
        return 'S'
    if score >= THRESHOLD:
        return 'A'
    return 'B'
