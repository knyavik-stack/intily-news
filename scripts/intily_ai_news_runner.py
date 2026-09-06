"""Production entrypoint for Intily with the current deterministic editorial policy.

The legacy publisher remains the operational engine. This thin entrypoint applies
policy overrides before calling its main(), keeping the publication pipeline,
state format and Telegram delivery unchanged while allowing scoring policy to be
versioned independently and tested without network calls.
"""

import importlib

from intily_scoring_policy import calculate, tier


def apply_policy(publisher):
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
        return value

    publisher.score = score

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
