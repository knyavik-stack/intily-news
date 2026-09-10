import json
import unittest
from unittest.mock import patch
import urllib.error

from intily_production_entrypoint import (
    AI_EVALUATION_BUDGET_SECONDS,
    CANONICAL_PRE_AI_THRESHOLD,
    GEMINI_MAX_PROMPT_CHARS,
    GEMINI_REQUEST_TIMEOUT_SECONDS,
    _compact_gemini_prompt,
    _groq_chat,
    _one_shot_gemini_chat,
    _sync_provider_credentials,
)


class ProductionEntrypointTests(unittest.TestCase):
    def test_canonical_pre_ai_threshold_is_40(self):
        self.assertEqual(CANONICAL_PRE_AI_THRESHOLD, 40.0)

    def test_ai_evaluation_budget_leaves_workflow_safety_margin(self):
        self.assertGreaterEqual(AI_EVALUATION_BUDGET_SECONDS, 120.0)
        self.assertLessEqual(AI_EVALUATION_BUDGET_SECONDS, 180.0)

    def test_gemini_request_timeout_is_bounded(self):
        self.assertLessEqual(GEMINI_REQUEST_TIMEOUT_SECONDS, 20)

    def test_gemini_quota_429_fails_without_retry(self):
        error_body = json.dumps({'error': {'code': 'quota_exceeded', 'message': 'You exceeded your current quota.'}}).encode()
        error = urllib.error.HTTPError('https://example.invalid', 429, 'quota', {'Content-Type': 'application/json'}, None)
        error.read = lambda: error_body
        with patch('intily_production_entrypoint.urllib.request.urlopen', side_effect=error) as mocked:
            with patch('intily_production_entrypoint.time.sleep'):
                with self.assertRaisesRegex(RuntimeError, r'GEMINI_HTTP_429'):
                    _one_shot_gemini_chat('test', 'token')
        self.assertEqual(mocked.call_count, 1)

    def test_gemini_transient_429_retries_with_backoff(self):
        first = urllib.error.HTTPError('https://example.invalid', 429, 'rate', {'Content-Type': 'application/json'}, None)
        first.read = lambda: json.dumps({'error': {'code': 'rate_limit_exceeded'}}).encode()

        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self):
                return json.dumps({'candidates': [{'content': {'parts': [{'text': '{"audience_score":8}'}]}}]}).encode()

        calls = [first, FakeResponse()]
        def fake_urlopen(*args, **kwargs):
            value = calls.pop(0)
            if isinstance(value, Exception): raise value
            return value

        with patch('intily_production_entrypoint.urllib.request.urlopen', side_effect=fake_urlopen) as mocked:
            with patch('intily_production_entrypoint.time.sleep') as sleep:
                result = _one_shot_gemini_chat('test', 'token')
        self.assertEqual(result, '{"audience_score":8}')
        self.assertEqual(mocked.call_count, 2)
        self.assertTrue(any(call.args and call.args[0] == 2.0 for call in sleep.call_args_list))

    def test_gemini_prompt_is_bounded(self):
        long_prompt = 'x' * (GEMINI_MAX_PROMPT_CHARS + 5000)
        compacted = _compact_gemini_prompt(long_prompt)
        self.assertEqual(len(compacted), GEMINI_MAX_PROMPT_CHARS)

    def test_groq_uses_explicit_user_agent(self):
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self):
                return json.dumps({'choices': [{'message': {'content': '{"audience_score":8}'}}]}).encode()

        captured = {}
        def fake_urlopen(request, timeout):
            captured['request'] = request
            captured['timeout'] = timeout
            return FakeResponse()

        with patch('intily_production_entrypoint.urllib.request.urlopen', side_effect=fake_urlopen):
            result = _groq_chat('https://api.groq.com/openai/v1/chat/completions', 'llama-3.1-8b-instant', 'token', 'test')

        self.assertEqual(result, '{"audience_score":8}')
        self.assertEqual(captured['timeout'], 20)
        self.assertEqual(captured['request'].headers['User-agent'], 'IntilyAI-News/7.0')

    def test_groq_cloudflare_1010_is_not_retried(self):
        error = urllib.error.HTTPError('https://api.groq.com', 403, 'forbidden', {}, None)
        error.read = lambda: b'error code: 1010'
        with patch('intily_production_entrypoint.urllib.request.urlopen', side_effect=error) as mocked:
            with self.assertRaisesRegex(RuntimeError, r'GROQ_HTTP_403'):
                _groq_chat('https://api.groq.com/openai/v1/chat/completions', 'llama-3.1-8b-instant', 'token', 'test')
        self.assertEqual(mocked.call_count, 1)

    def test_first_provider_migration_reset_reopens_existing_circuit(self):
        state = {'providers': {'OPENAI': {'disabled_until': 9999999999}}, '_provider_key_fingerprints': {}}
        with patch.dict('intily_production_entrypoint.os.environ', {'OPENAI_API_KEY': 'new-key'}, clear=False):
            _sync_provider_credentials(state)
        self.assertEqual(state['providers']['OPENAI']['disabled_until'], 0)
        self.assertIn('OPENAI', state['_provider_key_fingerprints'])

    def test_rotated_provider_key_reopens_existing_circuit(self):
        state = {'providers': {'OPENAI': {'disabled_until': 9999999999}}, '_provider_key_fingerprints': {'OPENAI': 'old-fingerprint'}}
        with patch.dict('intily_production_entrypoint.os.environ', {'OPENAI_API_KEY': 'new-key'}, clear=False):
            _sync_provider_credentials(state)
        self.assertEqual(state['providers']['OPENAI']['disabled_until'], 0)


if __name__ == '__main__':
    unittest.main()
