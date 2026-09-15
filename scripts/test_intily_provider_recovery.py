import json
import os
import tempfile
import unittest

from intily_provider_recovery import recover_if_all_blocked, recover_state


class ProviderRecoveryTests(unittest.TestCase):
    def test_recover_state_clears_only_provider_circuits(self):
        state = {
            'queue': [{'key': 'keep-me'}],
            'published': {'published-key': 1},
            'providers': {
                'GEMINI': {'disabled_until': 9999999999, 'reason': 'quota'},
                'GROQ': {'disabled_until': 9999999999, 'reason': '403'},
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'state.json')
            with open(path, 'w', encoding='utf-8') as handle:
                json.dump(state, handle)

            recovered = recover_state(path)

            with open(path, encoding='utf-8') as handle:
                result = json.load(handle)

        self.assertEqual(result['queue'], state['queue'])
        self.assertEqual(result['published'], state['published'])
        self.assertEqual(result['providers']['GEMINI']['disabled_until'], 0)
        self.assertEqual(result['providers']['GEMINI']['reason'], '')
        self.assertEqual(result['providers']['GROQ']['disabled_until'], 0)
        self.assertEqual(len(recovered), 2)

    def test_recover_if_all_blocked_resets_deadlock(self):
        state = {
            'queue': [{'key': 'keep-me'}],
            'providers': {
                'GEMINI': {'disabled_until': 9999999999, 'reason': 'quota'},
                'GROQ': {'disabled_until': 9999999999, 'reason': '429'},
                'OPENROUTER': {'disabled_until': 9999999999, 'reason': 'quota'},
                'OPENAI': {'disabled_until': 9999999999, 'reason': 'circuit'},
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'state.json')
            with open(path, 'w', encoding='utf-8') as handle:
                json.dump(state, handle)

            recovered = recover_if_all_blocked(path)

            with open(path, encoding='utf-8') as handle:
                result = json.load(handle)

        self.assertEqual(len(recovered), 4)
        self.assertEqual(result['queue'], state['queue'])
        for name in ('GEMINI', 'GROQ', 'OPENROUTER', 'OPENAI'):
            self.assertEqual(result['providers'][name]['disabled_until'], 0)
            self.assertEqual(result['providers'][name]['reason'], '')

    def test_github_token_does_not_count_as_available_ai_provider(self):
        state = {
            'providers': {
                'GEMINI': {'disabled_until': 9999999999, 'reason': 'quota'},
                'GROQ': {'disabled_until': 9999999999, 'reason': '429'},
                'OPENROUTER': {'disabled_until': 9999999999, 'reason': 'quota'},
                'OPENAI': {'disabled_until': 9999999999, 'reason': 'circuit'},
                'GITHUB_MODELS': {'disabled_until': 0, 'reason': ''},
            },
        }
        previous = os.environ.get('GITHUB_TOKEN')
        os.environ['GITHUB_TOKEN'] = 'test-token'
        try:
            with tempfile.TemporaryDirectory() as directory:
                path = os.path.join(directory, 'state.json')
                with open(path, 'w', encoding='utf-8') as handle:
                    json.dump(state, handle)

                recovered = recover_if_all_blocked(path)

                with open(path, encoding='utf-8') as handle:
                    result = json.load(handle)
        finally:
            if previous is None:
                os.environ.pop('GITHUB_TOKEN', None)
            else:
                os.environ['GITHUB_TOKEN'] = previous

        self.assertEqual(len(recovered), 4)
        self.assertEqual(result['providers']['GITHUB_MODELS']['disabled_until'], 0)
        self.assertEqual(result['providers']['GITHUB_MODELS']['reason'], '')

    def test_recover_if_all_blocked_does_not_reset_when_one_provider_is_available(self):
        state = {
            'providers': {
                'GEMINI': {'disabled_until': 9999999999, 'reason': 'quota'},
                'GROQ': {'disabled_until': 0, 'reason': ''},
                'OPENAI': {'disabled_until': 9999999999, 'reason': 'circuit'},
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'state.json')
            with open(path, 'w', encoding='utf-8') as handle:
                json.dump(state, handle)

            recovered = recover_if_all_blocked(path)

            with open(path, encoding='utf-8') as handle:
                result = json.load(handle)

        self.assertEqual(recovered, [])
        self.assertEqual(result['providers']['GEMINI']['disabled_until'], 9999999999)
        self.assertEqual(result['providers']['OPENAI']['disabled_until'], 9999999999)


if __name__ == '__main__':
    unittest.main()
