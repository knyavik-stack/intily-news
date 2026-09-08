"""Production scoring runtime guard.

The legacy runner assigns a temporary +10 audience bonus before the AI editor
has evaluated a story. That is not an editorial score: pre-AI must contain only
the deterministic 0–70 layer. This adapter intercepts the runner's score
assignment and restores the canonical contract without changing the runner's
other behavior.
"""

import functools


class PublisherScoreProxy:
    """Proxy that guards the score function installed by the legacy runner."""

    def __init__(self, module):
        object.__setattr__(self, "_module", module)

    def __getattr__(self, name):
        return getattr(self._module, name)

    def __setattr__(self, name, value):
        if name == "score" and callable(value):
            @functools.wraps(value)
            def guarded_score(item):
                result = value(item)
                if item.get("audience_score") is None:
                    components = item.get("_score_components") or {}
                    base_score = round(float(components.get("base_score", result)), 1)
                    components["audience_bonus"] = 0.0
                    components["final_score"] = base_score
                    item["_score_components"] = components
                    item["audience_bonus"] = 0.0
                    item["score_stage"] = "pre_ai"
                    return base_score
                return result

            setattr(self._module, name, guarded_score)
            return
        setattr(self._module, name, value)


def run_production():
    import importlib

    runner = importlib.import_module("intily_ai_news_runner")
    publisher_module = importlib.import_module("intily_ai_news")
    publisher = PublisherScoreProxy(publisher_module)

    runner.apply_policy(publisher)
    runner.apply_image_delivery(publisher)
    publisher.main()


if __name__ == "__main__":
    run_production()
