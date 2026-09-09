import unittest
from unittest.mock import patch
import urllib.error

from intily_production_entrypoint import (
    CANONICAL_PRE_AI_THRESHOLD,
    GITHUB_MODELS_MODEL,
    _github_models_chat,
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

    def test_github_models_uses_openai_compatible_endpoint(self):
        payload = {
            'choices': [{'message': {'content': '{"ok":true}'}}]
        }

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                import json
                return json.dumps(payload).encode()

        def fake_urlopen(request, timeout):
            self.assertEqual(timeout, 25)
            self.assertIn('models.github.ai/inference/chat/completions', request.full_url)
            self.assertEqual(request.headers['Authorization'], 'Bearer token')
            return FakeResponse()

        with patch('intily_production_entrypoint.urllib.request.urlopen', side_effect=fake_urlopen):
            result = _github_models_chat('test', 'token')

        self.assertEqual(result, '{"ok":true}')
        self.assertEqual(GITHUB_MODELS_MODEL, 'openai/gpt-4o')


if __name__ == '__main__':
    unittest.main()
