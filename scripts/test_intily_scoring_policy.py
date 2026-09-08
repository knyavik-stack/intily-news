import unittest
from datetime import datetime, timezone

import intily_ai_news as publisher
from intily_scoring_policy import BASE_MAX, THRESHOLD, calculate, tier


class ScoringPolicyTests(unittest.TestCase):
    def score(self, title, desc, source='Reuters'):
        item = {
            'title': title,
            'desc': desc,
            'source': source,
            'time': datetime.now(timezone.utc).timestamp(),
        }
        return calculate(
            item,
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

    def test_base_model_has_explicit_seventy_point_ceiling(self):
        self.assertEqual(BASE_MAX, 70.0)

    def test_relevant_concrete_release_has_material_base_score(self):
        value, parts = self.score(
            'OpenAI launches a new reasoning model for enterprise coding',
            'OpenAI released the model today with lower latency and a larger context window for production software teams.'
        )
        self.assertGreaterEqual(value, 40.0)
        self.assertGreater(parts['event_concreteness'], 0)
        self.assertGreater(parts['impact'], 0)

    def test_major_acquisition_has_strong_base_materiality(self):
        value, parts = self.score(
            'Nvidia acquires AI infrastructure startup for $8 billion',
            'The acquisition expands Nvidia capacity for AI inference and enterprise deployment.'
        )
        self.assertGreaterEqual(value, 40.0)
        self.assertGreaterEqual(parts['event_concreteness'], 14.0)

    def test_generic_ai_commentary_does_not_clear_final_gate_by_itself(self):
        value, _parts = self.score(
            'AI market trends continue to shape technology',
            'Analysts discuss how artificial intelligence may affect software and business over time.'
        )
        self.assertLess(value, THRESHOLD)

    def test_non_ai_story_is_zero_relevance(self):
        value, parts = self.score(
            'Major semiconductor factory opens in Europe',
            'The factory will produce chips for consumer electronics.'
        )
        self.assertEqual(parts['relevance'], 0.0)
        self.assertLess(value, THRESHOLD)


if __name__ == '__main__':
    unittest.main()
