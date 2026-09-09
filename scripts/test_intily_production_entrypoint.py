import unittest
from unittest.mock import patch
import urllib.error

from intily_production_entrypoint import (
    CANONICAL_PRE_AI_THRESHOLD,
    _one_shot_gemini_chat,
)


class ProductionEntrypointTests(unittest.TestCase):
    def test_canonical_pre_ai_threshold_is_40(self):
        self.assertEqual(CANONICAL_PRE_AI_THRESHOLD, 40.0)

    def test_gemini_429_fails_fast_without_retry(self):
        error = urllib.error.HTTPError(
            'https://example.invalid',
            429,
            'quota',
            {'Content-Type': 'application/json'},
            None,
        )
        with patch('intily_production_entrypoint.urllib.request.urlopen', side_effect=error) as mocked:
            with self.assertRaisesRegex(RuntimeError, r'GEMINI_HTTP_429'):
                _one_shot_gemini_chat('test', 'token')
        self.assertEqual(mocked.call_count, 1)


if __name__ == '__main__':
    unittest.main()
