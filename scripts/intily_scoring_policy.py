"""Intily editorial scoring policy v2.

The score is an editorial-materiality score, not a keyword-density score.
60 is the production publication gate: a concrete, materially useful AI event
should normally land around 60-75; 75+ is major industry news; 85+ is
exceptional/channel-defining.

The model is deliberately event-first. AI relevance establishes the domain,
then concrete event materiality and impact do most of the discrimination.
Semantic story memory remains responsible for uniqueness/deduplication.
"""

from datetime import datetime, timezone

THRESHOLD = 60.0

WEIGHTS = {
    'relevance': 20.0,
    'ai_specificity': 10.0,
    'impact': 20.0,
    'event_concreteness': 20.0,
    'practical_value': 10.0,
    'novelty': 4.0,
    'source_quality': 8.0,
    'evidence': 4.0,
    'freshness': 4.0,
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
        return 4.0
    if age_hours <= 3.0:
        return 3.0
    if age_hours <= 6.0:
        return 2.0
    if age_hours <= 12.0:
        return 1.0
    return 0.0


def _event_concreteness(blob, title):
    families = (
        ('launch', ('launch', 'launched', 'debut', 'запуст', 'старт')),
        ('release', ('release', 'released', 'version', 'релиз', 'выпуст', 'обновлен', 'представ')),
        ('deal', ('acquisition', 'acquired', 'merger', 'partnership', 'agreement', 'поглощ', 'приобр', 'слиян', 'партнёр', 'партнер', 'соглашен', 'сделк')),
        ('money', ('funding', 'investment', 'invest', 'revenue', 'billion', 'million', 'финансир', 'инвестиц', 'выручк', 'миллиард', 'млн')),
        ('research', ('study', 'research', 'paper', 'experiment', 'trial', 'исследован', 'эксперимент', 'испытан', 'отчёт', 'отчет')),
        ('policy', ('regulation', 'law', 'approved', 'regulator', 'регулир', 'закон', 'одобр', 'регулятор')),
        ('incident', ('breach', 'outage', 'incident', 'vulnerability', 'attack', 'утеч', 'сбой', 'инцидент', 'уязвим', 'атак')),
    )
    hits = [name for name, terms in families if any(term in blob for term in terms)]
    if not hits:
        return 0.0
    value = 11.0 + min(6.0, max(0, len(hits) - 1) * 3.0)
    if any(ch.isdigit() for ch in title):
        value += 2.0
    if any(term in blob for term in ('today', 'announced', 'announces', 'now', 'сегодня', 'объявил', 'объявила', 'объявляет')):
        value += 1.0
    return min(WEIGHTS['event_concreteness'], value)


def _ai_specificity(blob, ai_terms):
    hits = _distinct_hits(blob, ai_terms)
    if not hits:
        return 0.0
    return min(WEIGHTS['ai_specificity'], 4.0 + max(0, hits - 1) * 1.5)


def _impact(blob, high_impact_terms, risk_terms):
    impact_hits = _distinct_hits(blob, high_impact_terms)
    risk_hits = _distinct_hits(blob, risk_terms)
    if not impact_hits and not risk_hits:
        return 0.0
    value = 6.0 + min(9.0, max(0, impact_hits - 1) * 2.25)
    value += min(5.0, risk_hits * 2.5)
    return min(WEIGHTS['impact'], value)


def _practical(blob, application_terms, practical_terms):
    hits = _distinct_hits(blob, set(application_terms) | set(practical_terms))
    if not hits:
        return 0.0
    return min(WEIGHTS['practical_value'], 3.0 + max(0, hits - 1) * 1.5)


def _novelty(blob, title, exclusivity_terms):
    hits = _distinct_hits(title + ' ' + blob, exclusivity_terms)
    value = min(2.0, hits * 1.0)
    if any(ch.isdigit() for ch in title):
        value += 1.0
    if any(term in blob for term in ('surpass', 'beats', 'ahead', 'faster', 'cheaper', 'лучше', 'быстрее', 'дешевле', 'превзош', 'рекорд')):
        value += 1.0
    return min(WEIGHTS['novelty'], value)


def _evidence(desc):
    length = len(' '.join(str(desc or '').split()))
    if length < 50:
        return 0.5
    if length < 140:
        return round(0.5 + (length - 50) / 90.0 * 1.5, 1)
    if length < 320:
        return round(2.0 + (length - 140) / 180.0 * 2.0, 1)
    return 4.0


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
        'practical_value': _practical(blob, application_terms, practical_terms),
        'novelty': _novelty(blob, title, exclusivity_terms),
        'source_quality': 8.0 if source in quality_trusted else (6.0 if source in trusted else 4.0),
        'evidence': _evidence(x.get('desc', '')),
        'freshness': _freshness(_age_hours(x)),
    }
    penalty = 6.0 if _distinct_hits(blob, low_signal_terms) else 0.0
    parts['low_signal_penalty'] = penalty
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
