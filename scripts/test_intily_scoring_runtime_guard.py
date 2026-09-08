import unittest

from intily_scoring_runtime_guard import PublisherScoreProxy


class ScoringRuntimeGuardTests(unittest.TestCase):
    def test_pre_ai_score_contains_only_base_layer(self):
        class Module:
            pass

        module = Module()
        proxy = PublisherScoreProxy(module)

        def legacy_score(item):
            base = 70.0
            item['_score_components'] = {
                'base_score': base,
                'audience_bonus': 10.0,
                'final_score': 80.0,
            }
            item['audience_bonus'] = 10.0
            return 80.0

        proxy.score = legacy_score
        item = {}
        result = proxy.score(item)

        self.assertEqual(result, 70.0)
        self.assertEqual(item['audience_bonus'], 0.0)
        self.assertEqual(item['_score_components']['final_score'], 70.0)
        self.assertEqual(item['score_stage'], 'pre_ai')

    def test_ai_score_preserves_real_audience_bonus(self):
        class Module:
            pass

        module = Module()
        proxy = PublisherScoreProxy(module)

        def legacy_score(item):
            base = 70.0
            bonus = 30.0 if item.get('audience_score') == 10 else 0.0
            return base + bonus

        proxy.score = legacy_score
        item = {'audience_score': 10}
        self.assertEqual(proxy.score(item), 100.0)


if __name__ == '__main__':
    unittest.main()
