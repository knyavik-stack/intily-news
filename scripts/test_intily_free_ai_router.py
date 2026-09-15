import unittest
from unittest.mock import patch

import intily_free_ai_router as router


class FreeAIRouterTests(unittest.TestCase):
    def test_openrouter_quota_is_classified_as_daily(self):
        self.assertEqual(
            router._quota_reason('OPENROUTER', 'OPENROUTER_HTTP_429: daily limit exceeded'),
            'DAILY_QUOTA_OR_CREDITS',
        )

    def test_transient_429_is_not_daily_quota(self):
        self.assertEqual(
            router._quota_reason('GEMINI', 'GEMINI_HTTP_429: too many requests'),
            'HTTP_429_RATE_LIMIT',
        )

    def test_ai_cap_is_two(self):
        self.assertEqual(router.MAX_AI_EVAL_PER_CYCLE, 2)

    def test_free_router_model_is_zero_cost_router(self):
        self.assertEqual(router.OPENROUTER_MODEL, 'openrouter/free')

    def test_openrouter_request_shape(self):
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                return b'{"choices":[{"message":{"content":"{\\"title\\":\\"x\\",\\"body\\":\\"y\\"}"}}]}'

        with patch('intily_free_ai_router.urllib.request.urlopen', return_value=Response()) as call:
            result = router._openrouter_chat('test prompt', 'secret')
        self.assertIn('title', result)
        request = call.call_args.args[0]
        self.assertIn('Bearer secret', request.headers.get('Authorization', ''))


if __name__ == '__main__':
    unittest.main()
