import collections
import base64
import copy
import math

from rollbar.lib import transforms, python_major_version
from rollbar.lib.transforms.serializable import SerializableTransform

from rollbar.test import BaseTest, SNOWMAN, SNOWMAN_UNICODE

if python_major_version() >= 3:
    SNOWMAN = SNOWMAN_UNICODE

SNOWMAN_LEN = len(SNOWMAN)


# This base64 encoded string contains bytes that do not
# convert to utf-8 data
invalid_b64 = b'CuX2JKuXuLVtJ6l1s7DeeQ=='

invalid = base64.b64decode(invalid_b64)
binary_type_name = 'str' if python_major_version() < 3 else 'bytes'
undecodable_repr = '<Undecodable type:(%s) base64:(%s)>' % (binary_type_name, invalid_b64.decode('ascii'))


class SerializableTransformTest(BaseTest):
    def _assertSerialized(self, start, expected, safe_repr=True, whitelist=None, skip_id_check=False):
        serializable = SerializableTransform(safe_repr=safe_repr, whitelist_types=whitelist)
        result = transforms.transform(start, [serializable])

        """
        #print start
        print result
        print expected
        """

        if not skip_id_check:
            self.assertNotEqual(id(result), id(expected))

        self.assertEqual(type(expected), type(result))

        if isinstance(result, collections.Mapping):
            self.assertDictEqual(result, expected)
        elif isinstance(result, tuple):
            self.assertTupleEqual(result, expected)
        elif isinstance(result, (list, set)):
            self.assertListEqual(result, expected)
        else:
            self.assertEqual(result, expected)

    def test_simple_dict(self):
        start = {
            'hello': 'world',
            '1': 2,
        }
        expected = copy.deepcopy(start)
        self._assertSerialized(start, expected)

    def test_encode_dict_with_invalid_utf8(self):
        start = {
            'invalid': invalid
        }
        expected = copy.copy(start)
        expected['invalid'] = undecodable_repr
        self._assertSerialized(start, expected)

    def test_encode_utf8(self):
        start = invalid
        expected = undecodable_repr
        self._assertSerialized(start, expected)

    def test_encode_None(self):
        start = None
        expected = None
        self._assertSerialized(start, expected, skip_id_check=True)

    def test_encode_float(self):
        start = 3.14
        expected = 3.14
        self._assertSerialized(start, expected, skip_id_check=True)

    def test_encode_int(self):
        start = 33
        expected = 33
        self._assertSerialized(start, expected, skip_id_check=True)

    def test_encode_NaN(self):
        start = float('nan')

        serializable = SerializableTransform()
        result = transforms.transform(start, [serializable])

        self.assertTrue(math.isnan(result))

    def test_encode_Infinity(self):
        start = float('inf')

        serializable = SerializableTransform()
        result = transforms.transform(start, [serializable])

        self.assertTrue(math.isinf(result))

    def test_encode_empty_tuple(self):
        start = ()
        expected = ()
        self._assertSerialized(start, expected)

    def test_encode_empty_list(self):
        start = []
        expected = []
        self._assertSerialized(start, expected)

    def test_encode_empty_dict(self):
        start = {}
        expected = {}
        self._assertSerialized(start, expected)

    def test_encode_namedtuple(self):
        MyType = collections.namedtuple('MyType', ('field_1', 'field_2'))
        nt = MyType(field_1='this is field 1', field_2=invalid)

        start = nt
        if python_major_version() < 3:
            expected = "<MyType(field_1='this is field 1', field_2=u'%s')>" % undecodable_repr
        else:
            expected = "<MyType(field_1='this is field 1', field_2='%s')>" % undecodable_repr

        self._assertSerialized(start, expected)

    def test_encode_tuple_with_bytes(self):
        start = ('hello', 'world', invalid)
        expected = list(start)
        expected[2] = undecodable_repr
        self._assertSerialized(start, tuple(expected))

    def test_encode_list_with_bytes(self):
        start = ['hello', 'world', invalid]
        expected = list(start)
        expected[2] = undecodable_repr
        self._assertSerialized(start, expected)

    def test_encode_dict_with_bytes(self):
        start = {'hello': 'world', 'invalid': invalid}
        expected = copy.deepcopy(start)
        expected['invalid'] = undecodable_repr
        self._assertSerialized(start, expected)

    def test_encode_dict_with_bytes_key(self):
        start = {'hello': 'world', invalid: 'works?'}
        expected = copy.deepcopy(start)
        expected[undecodable_repr] = 'works?'
        del expected[invalid]
        self._assertSerialized(start, expected)

    def test_encode_with_custom_repr_no_whitelist(self):
        class CustomRepr(object):
            def __repr__(self):
                return 'hello'

        start = {'hello': 'world', 'custom': CustomRepr()}
        expected = copy.deepcopy(start)
        expected['custom'] = str(CustomRepr)
        self._assertSerialized(start, expected)

    def test_encode_with_custom_repr_no_whitelist_no_safe_repr(self):
        class CustomRepr(object):
            def __repr__(self):
                return 'hello'

        start = {'hello': 'world', 'custom': CustomRepr()}
        expected = copy.deepcopy(start)
        expected['custom'] = 'hello'
        self._assertSerialized(start, expected, safe_repr=False)

    def test_encode_with_custom_repr_whitelist(self):
        class CustomRepr(object):
            def __repr__(self):
                return 'hello'

        start = {'hello': 'world', 'custom': CustomRepr()}
        expected = copy.deepcopy(start)
        expected['custom'] = 'hello'
        self._assertSerialized(start, expected, whitelist=[CustomRepr])

    def test_encode_with_custom_repr_returns_bytes(self):
        class CustomRepr(object):
            def __repr__(self):
                return b'hello'

        start = {'hello': 'world', 'custom': CustomRepr()}

        serializable = SerializableTransform(whitelist_types=[CustomRepr])
        result = transforms.transform(start, [serializable])

        if python_major_version() < 3:
            self.assertEqual(result['custom'], b'hello')
        else:
            self.assertRegex(result['custom'], "<class '.*CustomRepr'>")

    def test_encode_with_custom_repr_returns_object(self):
        class CustomRepr(object):
            def __repr__(self):
                return {'hi': 'there'}

        start = {'hello': 'world', 'custom': CustomRepr()}

        serializable = SerializableTransform(whitelist_types=[CustomRepr])
        result = transforms.transform(start, [serializable])
        self.assertRegex(result['custom'], "<class '.*CustomRepr'>")

    def test_encode_with_custom_repr_returns_unicode(self):
        class CustomRepr(object):
            def __repr__(self):
                return SNOWMAN

        start = {'hello': 'world', 'custom': CustomRepr()}
        expected = copy.deepcopy(start)
        expected['custom'] = SNOWMAN
        self._assertSerialized(start, expected, whitelist=[CustomRepr])

    def test_encode_with_bad_repr_doesnt_die(self):
        class CustomRepr(object):
            def __repr__(self):
                assert False

        start = {'hello': 'world', 'custom': CustomRepr()}
        serializable = SerializableTransform(whitelist_types=[CustomRepr])
        result = transforms.transform(start, [serializable])
        self.assertRegex(result['custom'], "<AssertionError.*CustomRepr.*>")

    def test_encode_with_bad_str_doesnt_die(self):

        class UnStringableException(Exception):
            def __str__(self):
                raise Exception('asdf')

        class CustomRepr(object):

            def __repr__(self):
                raise UnStringableException()

        start = {'hello': 'world', 'custom': CustomRepr()}
        serializable = SerializableTransform(whitelist_types=[CustomRepr])
        result = transforms.transform(start, [serializable])
        self.assertRegex(result['custom'], "<UnStringableException.*Exception.*str.*>")
