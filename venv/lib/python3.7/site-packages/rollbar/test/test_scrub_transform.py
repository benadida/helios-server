import collections
import copy

from rollbar.lib import transforms
from rollbar.lib.transforms.scrub import ScrubTransform

from rollbar.test import BaseTest, SNOWMAN


class ScrubTransformTest(BaseTest):
    def _assertScrubbed(self, suffixes, start, expected, redact_char='*', skip_id_check=False):
        scrubber = ScrubTransform(suffixes=suffixes, redact_char=redact_char, randomize_len=False)
        result = transforms.transform(start, [scrubber])

        """
        print start
        print result
        print expected
        """

        if not skip_id_check:
            self.assertNotEqual(id(result), id(expected))

        self.assertEqual(type(result), type(expected))

        if isinstance(result, collections.Mapping):
            self.assertDictEqual(result, expected)
        elif isinstance(result, tuple):
            self.assertTupleEqual(result, expected)
        elif isinstance(result, (list, set)):
            self.assertListEqual(result, expected)
        else:
            self.assertEqual(result, expected)

    def test_string(self):
        obj = 'simple_string'

        # The Python interpreter is pretty smart... let's fool it into
        # not using the same string object for the expected var
        expected = ('simple_string' + ' dummy').split()[0]
        self._assertScrubbed([['password']], obj, expected)

    def test_num(self):
        obj = 22
        expected = 22
        self._assertScrubbed([['password']], obj, expected, skip_id_check=True)

    def test_None(self):
        obj = None
        expected = None
        self._assertScrubbed([['password']], obj, expected, skip_id_check=True)

    def test_list_of_None(self):
        obj = [None, None, None]
        expected = [None, None, None]
        self._assertScrubbed([['password']], obj, expected)

    def test_no_suffixes(self):
        obj = {'hello': 'world', 'password': 'cleartext'}
        expected = dict(obj)
        self._assertScrubbed([], obj, expected)

    def test_scrub_simple_dict(self):
        obj = {'hello': 'world', 'password': 'cleartext'}
        expected = copy.deepcopy(obj)
        expected['password'] = '*********'
        self._assertScrubbed([['password']], obj, expected)

    def test_scrub_dict_in_list(self):
        obj = [{'hello': 'world', 'password': 'cleartext'}, 'another element']
        expected = copy.deepcopy(obj)
        expected[0]['password'] = '*********'
        self._assertScrubbed([['password']], obj, expected)

    def test_scrub_dict_in_tuple(self):
        obj = ({'hello': 'world', 'password': 'cleartext'}, 'another element')
        expected = copy.deepcopy(obj)
        expected[0]['password'] = '*********'
        self._assertScrubbed([['password']], obj, expected)

    def test_scrub_dict_in_dict(self):
        obj = {'the data': {'hello': 'world', 'password': 'cleartext'}, 'some other data': 3}
        expected = copy.deepcopy(obj)
        expected['the data']['password'] = '*********'
        self._assertScrubbed([['password']], obj, expected)

    def test_scrub_multiple_suffixes(self):
        obj = {'hello': 'world', 'password': 'cleartext'}
        expected = copy.deepcopy(obj)
        expected['hello'] = '*****'
        expected['password'] = '*********'
        self._assertScrubbed([['hello'], ['password']], obj, expected)

    def test_scrub_no_suffix_match(self):
        obj = {'hello': 'world', 'password': 'cleartext'}
        expected = copy.deepcopy(obj)
        self._assertScrubbed([['not found'], ['access_token']], obj, expected)

    def test_scrub_full_dict(self):
        obj = {'hello': 'world', 'password': {'nested': 'secrets'}}
        expected = copy.deepcopy(obj)
        expected['password'] = '*'
        self._assertScrubbed([['password']], obj, expected)

    def test_scrub_full_list(self):
        obj = {'hello': 'world', 'password': [1, 2, 3, 4]}
        expected = copy.deepcopy(obj)
        expected['password'] = '****'
        self._assertScrubbed([['password']], obj, expected)

    def test_scrub_full_dict_with_nested_secret(self):
        obj = {'hello': 'world', 'password': [{'password': 'secret', 'nested': {'password': 'secret!!!'}}]}
        expected = copy.deepcopy(obj)
        expected['password'] = '*'
        self._assertScrubbed([['password']], obj, expected)

    def test_scrub_one_secret_and_one_clear_reference(self):
        ref = {'scrub': 'me', 'some': 'times'}
        obj = {'hello': 'world', 'password': ref, 'should be clear': ref}
        expected = copy.deepcopy(obj)
        expected['password'] = '**'
        self._assertScrubbed([['password']], obj, expected)

    def test_scrub_circular(self):
        ref = {'scrub': 'me', 'some': 'times'}
        obj = {'hello': 'world', 'password': ref}
        ref['circular'] = obj
        """
        Obj A =
        {
          'hello': 'world',
          'password': {
            'scrub': 'me', 'some': 'times', 'circular': A
          }
        }
        """
        expected = copy.deepcopy(obj)
        expected['password'] = '***'

        self._assertScrubbed([['password']], obj, expected)

    def test_circular(self):
        ref = {'scrub': 'me', 'some': 'times'}
        obj = {'hello': 'world', 'password': ref}
        ref['circular'] = obj

        scrubber = ScrubTransform([])
        result = transforms.transform(obj, [scrubber])

        self.assertIsNot(result, obj)
        self.assertIsNot(result['password'], ref)
        self.assertIsNot(result['password']['circular'], obj)
        self.assertIs(result['password']['circular']['password'], result['password']['circular']['password']['circular']['password'])

    def test_unicode_keys(self):
        obj = {
            SNOWMAN: 'hello'
        }
        expected = copy.deepcopy(obj)
        self._assertScrubbed([], obj, expected)

    def test_scrub_unicode_keys(self):
        obj = {
            SNOWMAN: 'hello'
        }
        expected = {
            SNOWMAN: '*****'
        }
        self._assertScrubbed([[SNOWMAN]], obj, expected)

    def test_scrub_unicode_values(self):
        obj = {
            'password': SNOWMAN
        }
        expected = {
            'password': '***'
        }
        self._assertScrubbed([['password']], obj, expected)

