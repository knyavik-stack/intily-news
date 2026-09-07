import unittest
from datetime import datetime, timezone

import intily_ai_news as publisher
from intily_scoring_policy import THRESHOLD, calculate, tier


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

    def test_relevant_concrete_release_clears_60(self):
        value, parts = self.score(
            'OpenAI launches a new reasoning model for enterprise coding',
            'OpenAI released the model today with lower latency and a larger context window for production software teams.'
        )
        self.assertGreaterEqual(value, THRESHOLD)
        self.assertGreater(parts['event_concreteness'], 0)
        self.assertGreater(parts['impact'], 0)
        self.assertEqual(tier(value), 'A')

    def test_major_acquisition_is_high_tier(self):
        value, _parts = self.score(
            'Nvidia acquires AI infrastructure startup for $8 billion',
            'The acquisition expands Nvidia capacity for AI inference and enterprise deployment.'
        )
        self.assertGreaterEqual(value, 75.0)

    def test_generic_ai_commentary_does_not_clear_gate(self):
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
