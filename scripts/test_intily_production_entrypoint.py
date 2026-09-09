import json
import unittest
from unittest.mock import patch
import urllib.error

from intily_production_entrypoint import (
    CANONICAL_PRE_AI_THRESHOLD,
    GEMINI_MAX_PROMPT_CHARS,
    GITHUB_MODELS_MODEL,
    _github_models_chat,
    _one_shot_gemini_chat,
)


class ProductionEntrypointTests(unittest.TestCase):
    def test_canonical_pre_ai_threshold_is_40(self):
        self.assertEqual(CANONICAL_PRE_AI_THRESHOLD, 40.0)

    def test_gemini_quota_429_fails_without_retry(self):
        error_body = json.dumps({
            'error': {
                'code': 'quota_exceeded',
                'message': 'You exceeded your current quota.'
            }
        }).encode()
        error = urllib.error.HTTPError(
            'https://example.invalid',
            429,
            'quota',
            {'Content-Type': 'application/json'},
            None,
        )
        error.read = lambda: error_body
        with patch('intily_production_entrypoint.urllib.request.urlopen', side_effect=error) as mocked:
            with patch('intily_production_entrypoint.time.sleep'):
                with self.assertRaisesRegex(RuntimeError, r'GEMINI_HTTP_429'):
                    _one_shot_gemini_chat('test', 'token')
        self.assertEqual(mocked.call_count, 1)

    def test_gemini_transient_429_retries_with_backoff(self):
        first = urllib.error.HTTPError(
            'https://example.invalid', 429, 'rate', {'Content-Type': 'application/json'}, None
        )
        first.read = lambda: json.dumps({'error': {'code': 'rate_limit_exceeded'}}).encode()

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps({
                    'candidates': [{'content': {'parts': [{'text': '{"audience_score":8}' }]}}]
                }).encode()

        calls = [first, FakeResponse()]

        def fake_urlopen(*args, **kwargs):
            value = calls.pop(0)
            if isinstance(value, Exception):
                raise value
            return value

        with patch('intily_production_entrypoint.urllib.request.urlopen', side_effect=fake_urlopen) as mocked:
            with patch('intily_production_entrypoint.time.sleep') as sleep:
                result = _one_shot_gemini_chat('test', 'token')

        self.assertEqual(result, '{"audience_score":8}')
        self.assertEqual(mocked.call_count, 2)
        self.assertTrue(any(call.args and call.args[0] == 2.0 for call in sleep.call_args_list))

    def test_gemini_prompt_is_bounded(self):
        long_prompt = 'x' * (GEMINI_MAX_PROMPT_CHARS + 5000)
        with patch('intily_production_entrypoint.urllib.request.urlopen') as mocked:
            response = type('Response', (), {
                '__enter__': lambda self: self,
                '__exit__': lambda self, *args: False,
                'read': lambda self: json.dumps({
                    'candidates': [{'content': {'parts': [{'text': '{"ok":true}' }]}}]
                }).encode(),
            })()
            mocked.return_value = response
            with patch('intily_production_entrypoint.time.sleep'):
                result = _one_shot_gemini_chat(long_prompt, 'token')
        self.assertEqual(result, '{"ok":true}')
        body = json.loads(mocked.call_args.kwargs['data'].decode())
        prompt_sent = body['contents'][0]['parts'][0]['text']
        self.assertLessEqual(len(prompt_sent), GEMINI_MAX_PROMPT_CHARS)

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
