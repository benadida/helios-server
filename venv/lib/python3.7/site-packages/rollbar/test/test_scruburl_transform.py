import copy

from rollbar.lib import map, transforms, string_types, urlparse, parse_qs, python_major_version
from rollbar.lib.transforms.scruburl import ScrubUrlTransform, _starts_with_auth_re

from rollbar.test import BaseTest, SNOWMAN, SNOWMAN_UNICODE

if python_major_version() >= 3:
    SNOWMAN = SNOWMAN_UNICODE

SNOWMAN_LEN = len(SNOWMAN)


class ScrubUrlTransformTest(BaseTest):
    def _assertScrubbed(self,
                        params_to_scrub,
                        start,
                        expected,
                        scrub_username=False,
                        scrub_password=True,
                        redact_char='-',
                        skip_id_check=False):
        scrubber = ScrubUrlTransform(suffixes=[],
                                     params_to_scrub=params_to_scrub,
                                     scrub_username=scrub_username,
                                     scrub_password=scrub_password,
                                     redact_char=redact_char,
                                     randomize_len=False)
        result = transforms.transform(start, [scrubber])

        """
        print(start)
        print(result)
        print(expected)
        """

        if not skip_id_check:
            self.assertNotEqual(id(result), id(expected))

        self.assertEqual(type(expected), type(result))
        self.assertIsInstance(result, string_types)
        self._compare_urls(expected, result)

    def _compare_urls(self, url1, url2):
        if _starts_with_auth_re.match(url1):
            url1 = '//%s' % url1

        if _starts_with_auth_re.match(url2):
            url2 = '//%s' % url2

        parsed_urls = map(urlparse, (url1, url2))
        qs_params = map(lambda x: parse_qs(x.query, keep_blank_values=True), parsed_urls)
        num_params = map(len, qs_params)
        param_names = map(lambda x: set(x.keys()), qs_params)

        self.assertEqual(*num_params)
        self.assertDictEqual(*qs_params)
        self.assertSetEqual(*param_names)

        for facet in ('scheme', 'netloc', 'path', 'params', 'username', 'password', 'hostname', 'port'):
            comp = map(lambda x: getattr(x, facet), parsed_urls)
            self.assertEqual(*comp)

    def test_no_scrub(self):
        obj = 'http://hello.com/?foo=bar'
        expected = obj
        self._assertScrubbed(['password'], obj, expected, skip_id_check=True)

    def test_not_url(self):
        obj = 'I am a plain\'ol string'
        expected = obj
        self._assertScrubbed(['password'], obj, expected, skip_id_check=True)

    def test_scrub_simple_url_params(self):
        obj = 'http://foo.com/asdf?password=secret'
        expected = obj.replace('secret', '------')
        self._assertScrubbed(['password'], obj, expected)

    def test_scrub_utf8_url_params(self):
        obj = 'http://foo.com/asdf?password=%s' % SNOWMAN
        expected = obj.replace(SNOWMAN, '-' * SNOWMAN_LEN)
        self._assertScrubbed(['password'], obj, expected)

    def test_scrub_utf8_url_keys(self):
        obj = 'http://foo.com/asdf?%s=secret' % SNOWMAN
        expected = obj.replace('secret', '------')
        self._assertScrubbed([str(SNOWMAN)], obj, expected)

    def test_scrub_multi_url_params(self):
        obj = 'http://foo.com/asdf?password=secret&password=secret2&token=TOK&clear=text'
        expected = obj.replace('secret2', '-------').replace('secret', '------').replace('TOK', '---')
        self._assertScrubbed(['password', 'token'], obj, expected)

    def test_scrub_password_auth(self):
        obj = 'http://cory:secr3t@foo.com/asdf?password=secret&clear=text'
        expected = obj.replace('secr3t', '------').replace('secret', '------')
        self._assertScrubbed(['password'], obj, expected)

    def test_scrub_username_auth(self):
        obj = 'http://cory:secr3t@foo.com/asdf?password=secret&clear=text'
        expected = obj.replace('cory', '----').replace('secret', '------')
        self._assertScrubbed(['password'], obj, expected, scrub_password=False, scrub_username=True)

    def test_scrub_username_and_password_auth(self):
        obj = 'http://cory:secr3t@foo.com/asdf?password=secret&clear=text'
        expected = obj.replace('cory', '----').replace('secr3t', '------').replace('secret', '------')
        self._assertScrubbed(['password'], obj, expected, scrub_password=True, scrub_username=True)

    def test_scrub_missing_scheme(self):
        obj = '//cory:secr3t@foo.com/asdf?password=secret&clear=text'
        expected = obj.replace('secr3t', '------').replace('secret', '------')
        self._assertScrubbed(['password'], obj, expected)

    def test_scrub_missing_scheme_and_double_slash(self):
        obj = 'cory:secr3t@foo.com/asdf?password=secret&clear=text'
        expected = obj.replace('secr3t', '------').replace('secret', '------')
        self._assertScrubbed(['password'], obj, expected)

    def test_keep_blank_url_params(self):
        obj = 'http://foo.com/asdf?foo=bar&baz='
        expected = obj
        self._assertScrubbed(['password'], obj, expected, skip_id_check=True)

    def test_scrub_dict_val_isnt_string(self):

        # This link will *not* be scrubbed because the value isn't a string or bytes
        obj = {
            'url': ['cory:secr3t@foo.com/asdf?password=secret&clear=text']
        }

        scrubber = ScrubUrlTransform(suffixes=[('url',)], params_to_scrub=['password'], randomize_len=False)
        result = transforms.transform(obj, [scrubber])

        expected = copy.deepcopy(obj)
        self.assertDictEqual(expected, result)

    def test_scrub_dict_nested_key_match_with_circular_ref(self):
        # If a URL is a circular reference then let's make sure to
        # show the scrubbed, original URL
        url = 'cory:secr3t@foo.com/asdf?password=secret&clear=text'
        obj = {
            'url': [{'link': url}],
            'link': [{'url': url}]
        }

        scrubber = ScrubUrlTransform(suffixes=[('url',), ('link',)], params_to_scrub=['password'], randomize_len=False)
        result = transforms.transform(obj, [scrubber])

        self.assertNotIn('secr3t', result['url'][0]['link'])
        self.assertNotIn('secret', result['url'][0]['link'])
        self.assertNotIn('secr3t', result['link'][0]['url'])
        self.assertNotIn('secret', result['link'][0]['url'])
        self.assertNotRegex(result['url'][0]['link'], r'^-+$')
        self.assertNotRegex(result['link'][0]['url'], r'^-+$')
