"""Production entrypoint for Intily with the current deterministic editorial policy.

The legacy publisher remains the operational engine. This thin entrypoint applies
policy overrides before calling its main(), keeping the publication pipeline,
state format and Telegram delivery unchanged while allowing scoring policy to be
versioned independently and tested without network calls.
"""

import importlib
import json

from intily_scoring_policy import THRESHOLD, calculate


def apply_policy(publisher):
    score_seen = set()
    score_buckets = {
        '0–39': 0,
        '40–49': 0,
        '50–59': 0,
        '60–69': 0,
        '70–79': 0,
        '80–84': 0,
        '85–89': 0,
        '90–100': 0,
    }

    def score(x):
        value, parts = calculate(
            x,
            publisher.ai_relevant,
            publisher.HIGH_IMPACT_TERMS,
            publisher.APPLICATION_TERMS,
            publisher.PRACTICAL_IMPLEMENTATION_TERMS,
            publisher.RISK_AND_PROBLEM_TERMS,
            publisher.EXCLUSIVITY_TERMS,
            publisher.QUALITY_TRUSTED,
            publisher.TRUSTED,
            publisher.LOW_SIGNAL_TERMS,
        )
        x['_score_components'] = parts
        identity = id(x)
        if identity not in score_seen:
            score_seen.add(identity)
            if value < 40:
                bucket = '0–39'
            elif value < 50:
                bucket = '40–49'
            elif value < 60:
                bucket = '50–59'
            elif value < 70:
                bucket = '60–69'
            elif value < 80:
                bucket = '70–79'
            elif value < 85:
                bucket = '80–84'
            elif value < 90:
                bucket = '85–89'
            else:
                bucket = '90–100'
            score_buckets[bucket] += 1
        return value

    publisher.score = score
    # The scoring module owns the admission threshold. Keeping the runtime
    # threshold in sync prevents the publisher's legacy 60-point constant from
    # silently rejecting items that the current policy considers admissible.
    publisher.IMPORTANCE_THRESHOLD = THRESHOLD

    original_collect = publisher.collect

    def collect_with_telemetry(telemetry=None):
        score_seen.clear()
        for key in score_buckets:
            score_buckets[key] = 0
        result = original_collect(telemetry)
        if telemetry is not None:
            telemetry['score_buckets'] = dict(score_buckets)
        print('SCORE_BUCKETS', json.dumps(score_buckets, ensure_ascii=False, separators=(',', ':')))
        return result

    publisher.collect = collect_with_telemetry

    # Geographic balance is a publication-priority rule, not an editorial-quality
    # weight. Disable the legacy random RU score bonus completely.
    publisher.RUSSIA_WEIGHT_BONUS_MIN = 0.0
    publisher.RUSSIA_WEIGHT_BONUS_MAX = 0.0

    # The legacy main() branch inverted the target: when RU share was low it
    # restricted publication to WORLD. Force that branch off and implement the
    # intended target in the priority function below.
    publisher.RUSSIA_TARGET_SHARE = -1.0

    def publication_region_boost(state, region):
        history = state.get('publication_regions', [])[-publisher.REGION_HISTORY_SIZE:]
        if not history:
            return 0.0
        ru_share = history.count('RUSSIA') / len(history)
        tolerance = 0.08
        target = 0.60
        if region == 'RUSSIA' and ru_share < target - tolerance:
            return 50.0
        if region == 'WORLD' and ru_share < target - tolerance:
            return -12.0
        if region == 'WORLD' and ru_share > target + tolerance:
            return 20.0
        if region == 'RUSSIA' and ru_share > target + tolerance:
            return -50.0
        return 0.0

    publisher.publication_region_boost = publication_region_boost


if __name__ == '__main__':
    publisher = importlib.import_module('intily_ai_news')
    apply_policy(publisher)
    publisher.main()
