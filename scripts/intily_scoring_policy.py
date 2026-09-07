"""Deterministic editorial scoring policy for Intily.

The score measures *editorial importance* on a 0..100 scale.  The production
admission gate is 60.0.  A score of 60 means a strong, concrete AI event worth
publishing; 75+ is a major industry event; 85+ is exceptional/channel-defining.

Uniqueness is NOT treated as a keyword synonym for importance. Source/query
syndication is handled by semantic story deduplication, while novelty is only
one component of the score.

The policy intentionally avoids raw keyword-count inflation. Each dimension has
an interpretable baseline and bounded increments, so a long article or a pile of
related words cannot manufacture importance.
"""

from datetime import datetime, timezone

THRESHOLD = 60.0

WEIGHTS = {
    'relevance': 25.0,
    'ai_specificity': 10.0,
    'impact': 15.0,
    'event_concreteness': 10.0,
    'practical_value': 10.0,
    'novelty': 8.0,
    'source_quality': 8.0,
    'evidence': 4.0,
    'freshness': 5.0,
    'timeliness': 5.0,
}


def _blob(x):
    return (x.get('title', '') + ' ' + x.get('desc', '') + ' ' + x.get('source', '')).lower()


def _hits(blob, terms):
    return sum(1 for term in terms if term in blob)


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
        return 2.5
    if age_hours <= 12.0:
        return 1.0
    return 0.0


def _timeliness(age_hours):
    if age_hours <= 1.0:
        return 5.0
    if age_hours <= 3.0:
        return 4.0
    if age_hours <= 6.0:
        return 2.5
    if age_hours <= 12.0:
        return 1.0
    return 0.0


def _evidence(desc):
    length = len(' '.join(str(desc or '').split()))
    if length < 50:
        return 0.5
    if length < 140:
        return round(0.5 + (length - 50) / 90.0 * 1.5, 1)
    if length < 320:
        return round(2.0 + (length - 140) / 180.0 * 2.0, 1)
    return 4.0


def _event_concreteness(blob, title):
    # Concrete event families get a meaningful baseline. This fixes the old
    # problem where one occurrence of "release" contributed only 2 points.
    event_families = (
        ('launch', ('launch', 'launched', 'debut', 'запуст', 'старт')),
        ('release', ('release', 'released', 'version', 'релиз', 'выпуст', 'обновлен')),
        ('deal', ('acquisition', 'acquired', 'merger', 'partnership', 'agreement', 'поглощ', 'приобр', 'слиян', 'партнёр', 'партнер', 'соглашен')),
        ('money', ('funding', 'investment', 'invest', 'revenue', 'billion', 'million', 'финансир', 'инвестиц', 'выручк', 'миллиард', 'млн')),
        ('research', ('study', 'research', 'paper', 'experiment', 'trial', 'исследован', 'эксперимент', 'испытан', 'отчёт', 'отчет')),
        ('policy', ('regulation', 'law', 'approved', 'regulator', 'регулир', 'закон', 'одобр', 'регулятор')),
        ('incident', ('breach', 'outage', 'incident', 'vulnerability', 'attack', 'утеч', 'сбой', 'инцидент', 'уязвим', 'атак')),
    )
    families = [name for name, terms in event_families if any(term in blob for term in terms)]
    if not families:
        return 0.0
    score = 4.5 + min(3.5, (len(families) - 1) * 1.5)
    if any(ch.isdigit() for ch in title):
        score += 1.0
    return min(WEIGHTS['event_concreteness'], score)


def _ai_specificity(blob, ai_terms):
    hits = _distinct_hits(blob, ai_terms)
    if not hits:
        return 0.0
    # Relevance already supplies the 25-point AI gate. Specificity rewards the
    # presence of distinct concrete AI concepts without turning repetition into
    # score inflation.
    return min(WEIGHTS['ai_specificity'], 3.5 + max(0, hits - 1) * 1.5)


def _impact(blob, high_impact_terms, risk_terms):
    impact_hits = _distinct_hits(blob, high_impact_terms)
    risk_hits = _distinct_hits(blob, risk_terms)
    if not impact_hits and not risk_hits:
        return 0.0

    # One meaningful impact signal establishes materiality; additional distinct
    # signals add resolution. Risk contributes here but is capped so it cannot
    # overpower an otherwise weak story.
    value = 5.5 + min(6.0, max(0, impact_hits - 1) * 1.75)
    value += min(3.0, risk_hits * 1.5)
    return min(WEIGHTS['impact'], value)


def _practical(blob, application_terms, practical_terms):
    hits = _distinct_hits(blob, set(application_terms) | set(practical_terms))
    if not hits:
        return 0.0
    return min(WEIGHTS['practical_value'], 3.0 + max(0, hits - 1) * 1.4)


def _novelty(blob, title, exclusivity_terms):
    exclusivity_hits = _distinct_hits(title + ' ' + blob, exclusivity_terms)
    has_number = any(ch.isdigit() for ch in title)
    has_comparison = any(term in blob for term in ('surpass', 'beats', 'ahead', 'faster', 'cheaper', 'лучше', 'быстрее', 'дешевле', 'превзош', 'рекорд'))
    value = min(4.0, exclusivity_hits * 2.0)
    if has_number:
        value += 1.5
    if has_comparison:
        value += 1.5
    return min(WEIGHTS['novelty'], value)


def score_components(x, ai_relevant, high_impact_terms, application_terms,
                     practical_terms, risk_terms, exclusivity_terms,
                     quality_trusted, trusted, low_signal_terms):
    blob = _blob(x)
    title = str(x.get('title', '') or '').strip().lower()
    source = str(x.get('source', '') or '').strip().lower()

    relevance = WEIGHTS['relevance'] if ai_relevant(x) else 0.0

    ai_terms = tuple(set(high_impact_terms) | set(application_terms) | set(practical_terms) | set(risk_terms) | set(exclusivity_terms))
    ai_specificity = _ai_specificity(blob, ai_terms)
    impact = _impact(blob, high_impact_terms, risk_terms)
    event_concreteness = _event_concreteness(blob, title)
    practical = _practical(blob, application_terms, practical_terms)
    novelty = _novelty(blob, title, exclusivity_terms)

    if source in quality_trusted:
        source_quality = 8.0
    elif source in trusted:
        source_quality = 6.0
    else:
        source_quality = 4.0

    evidence = _evidence(x.get('desc', ''))
    age_hours = _age_hours(x)
    freshness = _freshness(age_hours)
    timeliness = _timeliness(age_hours)
    penalty = 6.0 if _hits(blob, low_signal_terms) else 0.0

    return {
        'relevance': round(relevance, 1),
        'ai_specificity': round(ai_specificity, 1),
        'impact': round(impact, 1),
        'event_concreteness': round(event_concreteness, 1),
        'practical_value': round(practical, 1),
        'novelty': round(novelty, 1),
        'source_quality': round(source_quality, 1),
        'evidence': round(evidence, 1),
        'freshness': round(freshness, 1),
        'timeliness': round(timeliness, 1),
        'low_signal_penalty': round(penalty, 1),
    }


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
