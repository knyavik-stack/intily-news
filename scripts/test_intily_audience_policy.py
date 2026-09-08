import unittest

from intily_audience_policy import PRE_AI_THRESHOLD, FINAL_THRESHOLD, AUDIENCE_BONUS_MAX, bonus_from_score, clamp_score


class AudiencePolicyTests(unittest.TestCase):
    def test_two_stage_thresholds(self):
        self.assertEqual(PRE_AI_THRESHOLD, 40.0)
        self.assertEqual(FINAL_THRESHOLD, 55.0)

    def test_ai_layer_is_exactly_thirty_points(self):
        self.assertEqual(AUDIENCE_BONUS_MAX, 50.0)
        self.assertEqual(
            [bonus_from_score(i) for i in range(1, 11)],
            [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0],
        )

    def test_range_is_strict(self):
        self.assertEqual(clamp_score(8), 8.0)
        with self.assertRaises(ValueError):
            clamp_score(0)
        with self.assertRaises(ValueError):
            clamp_score(11)


if __name__ == '__main__':
    unittest.main()
