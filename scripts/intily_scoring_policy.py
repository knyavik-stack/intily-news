"""Intily editorial scoring policy v5.

The production score has two explicit layers:
- deterministic editorial base: 0-70 points;
- AI audience fit: 1-10 mapped to +3...+30 points.

v5 fixes a calibration defect: the previous component functions had generous
nominal allocations but conservative sub-formulas, so real AI stories clustered
around 40-52 and rarely exercised the upper half of the base scale. The new
model uses evidence tiers for consequence, event concreteness, specificity and
practical value. It does not add points merely because a story is long or names
a famous company.
"""

from datetime import datetime, timezone

THRESHOLD = 55.0
BASE_MAX = 70.0
AI_MAX = 30.0

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
    'launch': ('launch', 'launched', 'debut', 'unveils', 'unveiled', 'announc', 'запуст', 'старт', 'представ', 'анонс'),
    'release': ('release', 'released', 'version', 'rollout', 'available', 'релиз', 'выпуст', 'обновлен', 'обновил', 'новая модель', 'новый релиз'),
    'deal': ('acquisition', 'acquired', 'merger', 'partnership', 'agreement', 'поглощ', 'приобр', 'слиян', 'партнёр', 'партнер', 'соглашен', 'сделк'),
    'money': ('funding', 'investment', 'invested', 'financing', 'revenue', 'billion', 'million', 'финансир', 'инвестиц', 'выручк', 'миллиард', 'млн'),
    'research': ('study', 'research', 'paper', 'experiment', 'trial', 'findings', 'исследован', 'эксперимент', 'испытан', 'отчёт', 'отчет', 'исследование'),
    'policy': ('regulation', 'regulations', 'law', 'approved', 'regulator', 'policy', 'регулир', 'закон', 'одобр', 'регулятор', 'требован'),
    'incident': ('breach', 'outage', 'incident', 'vulnerability', 'exploit', 'attack', 'утеч', 'сбой', 'инцидент', 'уязвим', 'эксплойт', 'атак'),
}

MAJOR_ACTORS = (
    'openai', 'anthropic', 'google', 'deepmind', 'microsoft', 'meta', 'nvidia',
    'apple', 'amazon', 'xai', 'mistral', 'alibaba', 'baidu', 'sber', 'сбер',
    'yandex', 'яндекс', 'vk', 'росатом', 'perplexity', 'databricks',
)

MAJOR_EVENT_SIGNALS = (
    'flagship', 'frontier', 'state-of-the-art', 'breakthrough', 'record',
    'largest', 'first-ever', 'worldwide', 'global', 'national', 'critical',
    'впервые', 'прорыв', 'рекорд', 'крупнейш', 'миров', 'национальн', 'критическ',
)

MEASUREMENT_SIGNALS = (
    'benchmark', 'accuracy', 'performance', 'latency', 'cost', 'revenue', 'users',
    'employees', 'customers', 'percent', '%', 'billion', 'million', 'price',
    'бенчмарк', 'точност', 'производительност', 'задержк', 'стоимост', 'выручк',
    'пользовател', 'клиент', 'сотрудник', 'процент', 'миллиард', 'млн', 'цена',
)

PRACTICAL_SIGNALS = (
    'deployment', 'adoption', 'implementation', 'workflow', 'customer', 'revenue',
    'cost', 'roi', 'integration', 'production', 'developer', 'coding', 'automation',
    'enterprise', 'business', 'operations', 'inference', 'reliability',
    'внедрен', 'кейс', 'выручк', 'затрат', 'окупаем', 'процесс', 'операц',
    'интеграц', 'продакшн', 'разработ', 'программ', 'автоматизац', 'бизнес',
    'компани', 'производств', 'применен', 'инфраструктур',
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
    """Reward a verifiable event and its specificity, not raw keyword volume."""
    hits = [name for name, terms in EVENT_FAMILIES.items() if any(term in blob for term in terms)]
    if not hits:
        return 0.0

    primary = {
        'launch': 10.0,
        'release': 10.0,
        'deal': 12.0,
        'money': 9.0,
        'research': 9.0,
        'policy': 12.0,
        'incident': 12.0,
    }
    value = max(primary[name] for name in hits)
    # A second independent event family makes the event more concrete, but is
    # capped so repeated wording cannot inflate the score.
    value += min(2.0, max(0, len(hits) - 1) * 1.0)
    if any(actor in blob for actor in MAJOR_ACTORS):
        value += 3.0
    if any(signal in blob for signal in MAJOR_EVENT_SIGNALS):
        value += 2.0
    if any(term in blob for term in MEASUREMENT_SIGNALS):
        value += 1.0
    if any(ch.isdigit() for ch in title):
        value += 0.5
    return min(WEIGHTS['event_concreteness'], round(value, 1))


def _ai_specificity(blob, ai_terms):
    """Score concrete AI technology specificity in three evidence tiers."""
    hits = _distinct_hits(blob, ai_terms)
    if not hits:
        return 0.0
    if hits == 1:
        return 3.0
    if hits == 2:
        return 4.5
    if hits == 3:
        return 5.5
    return 6.0


def _impact(blob, high_impact_terms, risk_terms):
    """Estimate material consequence using scale, actor, measurement and risk."""
    impact_hits = _distinct_hits(blob, high_impact_terms)
    risk_hits = _distinct_hits(blob, risk_terms)
    actor = any(term in blob for term in MAJOR_ACTORS)
    major_signal = any(term in blob for term in MAJOR_EVENT_SIGNALS)
    measured = any(term in blob for term in MEASUREMENT_SIGNALS)

    if not impact_hits and not risk_hits:
        return 0.0

    # Baseline means there is a real consequence signal; subsequent tiers are
    # independent dimensions rather than keyword-count multiplication.
    value = 4.0
    if impact_hits >= 2:
        value += 3.0
    if impact_hits >= 4:
        value += 2.0
    if actor:
        value += 3.0
    if major_signal:
        value += 2.0
    if measured:
        value += 2.0
    if risk_hits:
        value += min(2.0, risk_hits * 1.0)
    return min(WEIGHTS['impact'], round(value, 1))


def _practical(blob):
    """Score real-world applicability in evidence tiers."""
    hits = _distinct_hits(blob, PRACTICAL_SIGNALS)
    if not hits:
        return 0.0
    if hits == 1:
        return 3.0
    if hits == 2:
        return 5.0
    if hits == 3:
        return 6.5
    return 8.0


def _source_quality(source, quality_trusted, trusted):
    source = source.strip().lower()
    if source in quality_trusted:
        return WEIGHTS['source_quality']
    if source in trusted:
        return 4.0
    return 2.0


def _evidence(desc):
    length = len(' '.join(str(desc or '').split()))
    if length < 50:
        return 0.3
    if length < 120:
        return 1.0
    if length < 220:
        return 2.0
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
    total = _clamp(base_total, 0.0, BASE_MAX)
    return round(total, 1), parts


def tier(score):
    if score >= 85.0:
        return 'S'
    if score >= THRESHOLD:
        return 'A'
    return 'B'
