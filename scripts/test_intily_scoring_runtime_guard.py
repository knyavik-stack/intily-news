import unittest

from intily_scoring_runtime_guard import PublisherScoreProxy, _attach_score_footer, _final_sort_key


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

    def test_final_score_is_primary_queue_order(self):
        items = [
            {'importance': 71.0, 'time': 300},
            {'importance': 94.0, 'time': 100},
            {'importance': 83.0, 'time': 200},
        ]
        ordered = sorted(items, key=_final_sort_key, reverse=True)
        self.assertEqual([x['importance'] for x in ordered], [94.0, 83.0, 71.0])

    def test_footer_contains_every_component_and_total(self):
        item = {
            '_score_components': {
                'base_score': 61.5,
                'relevance': 12.0,
                'ai_specificity': 5.5,
                'impact': 14.0,
                'event_concreteness': 15.0,
                'practical_value': 7.0,
                'novelty': 0.0,
                'source_quality': 5.0,
                'evidence': 2.0,
                'freshness': 2.0,
                'low_signal_penalty': 1.0,
                'audience_score': 9,
                'audience_bonus': 27.0,
                'final_score': 88.5,
            }
        }
        footer = _attach_score_footer(item, 'Основной текст новости')
        self.assertIn('Итого: 88.5/100', footer)
        self.assertIn('AI-релевантность: 12.0/12', footer)
        self.assertIn('AI-специфичность: 5.5/6', footer)
        self.assertIn('Влияние: 14.0/16', footer)
        self.assertIn('Конкретность события: 15.0/18', footer)
        self.assertIn('Практическая ценность: 7.0/8', footer)
        self.assertIn('Новизна: 0.0/0', footer)
        self.assertIn('Качество источника: 5.0/5', footer)
        self.assertIn('Доказательность: 2.0/3', footer)
        self.assertIn('Свежесть: 2.0/2', footer)
        self.assertIn('Аудитория: 9/10 → +27.0', footer)

    def test_footer_never_truncates_long_editorial_text(self):
        item = {'_score_components': {'base_score': 1, 'final_score': 1, 'audience_bonus': 0}}
        with self.assertRaisesRegex(RuntimeError, 'SCORE_DIAGNOSTICS_TEXT_LIMIT'):
            _attach_score_footer(item, 'x' * 4096)


if __name__ == '__main__':
    unittest.main()
