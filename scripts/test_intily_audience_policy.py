import unittest

from intily_audience_policy import PRE_AI_THRESHOLD, FINAL_THRESHOLD, bonus_from_score, clamp_score


class AudiencePolicyTests(unittest.TestCase):
    def test_two_stage_thresholds(self):
        self.assertEqual(PRE_AI_THRESHOLD, 45.0)
        self.assertEqual(FINAL_THRESHOLD, 60.0)

    def test_bonus_is_positive_only_above_neutral_fit(self):
        self.assertEqual(bonus_from_score(5), 0.0)
        self.assertEqual(bonus_from_score(6), 3.0)
        self.assertEqual(bonus_from_score(10), 15.0)

    def test_range_is_strict(self):
        self.assertEqual(clamp_score(8), 8.0)
        with self.assertRaises(ValueError):
            clamp_score(0)
        with self.assertRaises(ValueError):
            clamp_score(11)


if __name__ == '__main__':
    unittest.main()
