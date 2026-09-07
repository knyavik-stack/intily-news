import json
import unittest
from unittest.mock import patch

import intily_google_news as decoder


class GoogleNewsDecoderTests(unittest.TestCase):
    def test_non_google_url_is_unchanged(self):
        url = 'https://example.com/article'
        self.assertEqual(decoder.resolve(url), url)

    def test_params_are_extracted_from_article_shell(self):
        html = '<div data-n-a-sg="signature" data-n-a-ts="123456"></div>'
        self.assertEqual(decoder._params(html), ('signature', '123456'))

    def test_batchexecute_response_yields_publisher_url(self):
        inner = json.dumps(['ignored', 'https://publisher.example/article'])
        outer = json.dumps([['Fbv4je', None, inner]])
        raw = ')]}\'\n\n' + outer

        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *_args):
                return False
            def read(self):
                return raw.encode()

        with patch('intily_google_news.urllib.request.urlopen', return_value=Response()):
            resolved = decoder._batchexecute('article-id', 'sig', '123', 'CONSENT=PENDING+987')
        self.assertEqual(resolved, 'https://publisher.example/article')


if __name__ == '__main__':
    unittest.main()
