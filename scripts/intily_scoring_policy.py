"""Deterministic editorial scoring policy for Intily.

The score measures editorial quality/importance on a 0..100 scale.  The admission
threshold stays at the canonical production value of 60.0; calibration is done by
redistributing the score across independent dimensions rather than lowering the
gate to manufacture supply.

Geography is deliberately excluded from the editorial score. RUSSIA/WORLD balance
is handled separately by publication priority.
"""

from datetime import datetime, timezone

THRESHOLD = 60.0

# The previous policy concentrated too much weight in a binary relevance flag and
# then assigned small values to most other dimensions. Real production material
# therefore clustered below 60 even when it was clearly publishable.  The new
# model separates direct AI relevance from AI specificity, event concreteness and
# timeliness. This increases score resolution without changing the 60-point gate.
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


def _clamp(value, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(value)))


def _linear(value, maximum, scale):
    return min(maximum, max(0.0, float(value) * float(scale)))


def _age_hours(x):
    try:
        return max(0.0, (datetime.now(timezone.utc).timestamp() - float(x.get('time', 0) or 0)) / 3600.0)
    except Exception:
        return 24.0


def _freshness(age_hours):
    # General freshness: 5 -> 0 over 24 hours.
    return _clamp(5.0 * (1.0 - age_hours / 24.0), 0.0, 5.0)


def _timeliness(age_hours):
    # Separate early-cycle value: 5 -> 0 over the first 6 hours. This rewards
    # genuinely current events without making age a hard gate.
    return _clamp(5.0 * (1.0 - age_hours / 6.0), 0.0, 5.0)


def _evidence(desc):
    length = len(' '.join(str(desc or '').split()))
    if length <= 40:
        return round(length / 40.0 * 1.0, 1)
    if length <= 140:
        return round(1.0 + (length - 40) / 100.0 * 2.0, 1)
    return round(min(4.0, 3.0 + (length - 140) / 220.0), 1)


def _event_concreteness(blob, title):
    event_terms = (
        'announced', 'launch', 'launched', 'release', 'released', 'introduced',
        'acquired', 'acquisition', 'funding', 'invest', 'study', 'report',
        'partnership', 'agreement', 'approved', 'regulation', 'law', 'update',
        'запуст', 'выпуст', 'представ', 'объяв', 'купил', 'приобр', 'инвестиц',
        'исследован', 'отчёт', 'отчет', 'партнёр', 'партнер', 'соглашен',
        'одобр', 'регулир', 'закон', 'обновлен'
    )
    hits = _hits(blob, event_terms)
    numeric = 1 if any(ch.isdigit() for ch in title) else 0
    return min(WEIGHTS['event_concreteness'], hits * 2.0 + numeric * 2.0)


def _ai_specificity(blob, ai_terms):
    # Distinct AI concepts provide more resolution than the binary relevance gate.
    # Diminishing returns prevent keyword stuffing from dominating the score.
    hits = _hits(blob, ai_terms)
    return min(WEIGHTS['ai_specificity'], 4.0 + max(0, hits - 1) * 1.5) if hits else 0.0


def score_components(x, ai_relevant, high_impact_terms, application_terms,
                     practical_terms, risk_terms, exclusivity_terms,
                     quality_trusted, trusted, low_signal_terms):
    blob = _blob(x)
    title = str(x.get('title', '') or '').strip().lower()
    source = str(x.get('source', '') or '').strip().lower()

    relevance = WEIGHTS['relevance'] if ai_relevant(x) else 0.0

    ai_terms = tuple(set(high_impact_terms) | set(application_terms) | set(practical_terms) | set(risk_terms) | set(exclusivity_terms))
    ai_specificity = _ai_specificity(blob, ai_terms)

    impact_hits = _hits(blob, high_impact_terms)
    impact = min(WEIGHTS['impact'], impact_hits * 3.75)

    event_concreteness = _event_concreteness(blob, title)

    practical_hits = _hits(blob, application_terms) + _hits(blob, practical_terms)
    practical = min(WEIGHTS['practical_value'], practical_hits * 2.0)

    novelty_hits = _hits(title, exclusivity_terms)
    has_number = any(ch.isdigit() for ch in title)
    novelty = min(WEIGHTS['novelty'], novelty_hits * 2.0 + (2.0 if has_number else 0.0))

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

    # Risk is intentionally folded into impact/event concreteness through the
    # high-impact terms, while the final score remains 100 points exactly.
    risk_hits = _hits(blob, risk_terms)
    if risk_hits:
        impact = min(WEIGHTS['impact'], impact + min(3.0, risk_hits * 1.5))
        event_concreteness = min(WEIGHTS['event_concreteness'], event_concreteness + 1.0)

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
