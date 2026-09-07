import unittest

from intily_audience_policy import PRE_AI_THRESHOLD, FINAL_THRESHOLD, bonus_from_score, clamp_score


class AudiencePolicyTests(unittest.TestCase):
    def test_two_stage_thresholds(self):
        self.assertEqual(PRE_AI_THRESHOLD, 40.0)
        self.assertEqual(FINAL_THRESHOLD, 60.0)

    def test_bonus_is_linear_from_one_to_ten(self):
        self.assertEqual(
            [bonus_from_score(i) for i in range(1, 11)],
            [2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0],
        )

    def test_range_is_strict(self):
        self.assertEqual(clamp_score(8), 8.0)
        with self.assertRaises(ValueError):
            clamp_score(0)
        with self.assertRaises(ValueError):
            clamp_score(11)


if __name__ == '__main__':
    unittest.main()
