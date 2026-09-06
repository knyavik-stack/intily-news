"""Deterministic editorial scoring policy for Intily.

The score is editorial importance, not publication priority. Geography is handled
separately by the regional publication policy so RUSSIA/WORLD balancing never
artificially changes the underlying news quality score.
"""

from datetime import datetime, timezone

THRESHOLD = 60.0

# Maximum contribution of each editorial dimension; totals exactly 100.
WEIGHTS = {
    'relevance': 25.0,
    'impact': 18.0,
    'practical_value': 15.0,
    'novelty': 12.0,
    'source_quality': 10.0,
    'evidence': 8.0,
    'freshness': 7.0,
    'risk_significance': 5.0,
}


def _blob(x):
    return (x.get('title', '') + ' ' + x.get('desc', '') + ' ' + x.get('source', '')).lower()


def _hits(blob, terms):
    return sum(1 for term in terms if term in blob)


def _capped_hits(blob, terms, cap, step):
    return min(cap, _hits(blob, terms) * step)


def _clamp(value, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(value)))


def _freshness(age_hours):
    # Continuous decay instead of coarse buckets. Freshness is 7 points at 0h,
    # reaches 0 at 12h, and therefore creates meaningful one-decimal separation.
    return _clamp(7.0 * (1.0 - max(0.0, age_hours) / 12.0), 0.0, 7.0)


def _evidence(desc):
    length = len(' '.join(str(desc or '').split()))
    # 0..8 points, with diminishing returns. Empty/very short feed descriptions
    # receive little evidence credit; long descriptions do not dominate the score.
    if length <= 35:
        return round(length / 35.0 * 2.0, 1)
    if length <= 120:
        return round(2.0 + (length - 35) / 85.0 * 3.0, 1)
    return round(min(8.0, 5.0 + (length - 120) / 180.0 * 3.0), 1)


def score_components(x, ai_relevant, high_impact_terms, application_terms,
                     practical_terms, risk_terms, exclusivity_terms,
                     quality_trusted, trusted, low_signal_terms):
    blob = _blob(x)
    title = str(x.get('title', '') or '').strip().lower()
    source = str(x.get('source', '') or '').strip().lower()

    relevance = WEIGHTS['relevance'] if ai_relevant(x) else 0.0

    impact_hits = _hits(blob, high_impact_terms)
    impact = min(WEIGHTS['impact'], 5.0 + max(0, impact_hits - 1) * 3.0) if impact_hits else 0.0

    practical_hits = _hits(blob, application_terms)
    practical_hits += _hits(blob, practical_terms)
    practical = min(WEIGHTS['practical_value'], practical_hits * 2.0)

    novelty_hits = _hits(title, exclusivity_terms)
    # Numeric specificity is a useful novelty signal for releases, funding,
    # benchmarks and measurable events, but never enough to qualify alone.
    has_number = any(ch.isdigit() for ch in title)
    novelty = min(WEIGHTS['novelty'], novelty_hits * 3.0 + (2.0 if has_number else 0.0))

    source_quality = 8.0 if source in quality_trusted else (6.0 if source in trusted else 4.0)
    if source in quality_trusted:
        source_quality = 10.0
    elif source in trusted:
        source_quality = 7.0

    evidence = _evidence(x.get('desc', ''))

    try:
        age_hours = (datetime.now(timezone.utc).timestamp() - float(x.get('time', 0) or 0)) / 3600.0
    except Exception:
        age_hours = 12.0
    freshness = _freshness(age_hours)

    risk_hits = _hits(blob, risk_terms)
    risk_significance = min(WEIGHTS['risk_significance'], risk_hits * 2.0)

    penalty = 8.0 if _hits(blob, low_signal_terms) else 0.0

    return {
        'relevance': round(relevance, 1),
        'impact': round(impact, 1),
        'practical_value': round(practical, 1),
        'novelty': round(novelty, 1),
        'source_quality': round(source_quality, 1),
        'evidence': round(evidence, 1),
        'freshness': round(freshness, 1),
        'risk_significance': round(risk_significance, 1),
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
