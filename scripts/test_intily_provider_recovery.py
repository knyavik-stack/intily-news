import json
import os
import tempfile
import unittest

from intily_provider_recovery import recover_state


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


if __name__ == '__main__':
    unittest.main()
