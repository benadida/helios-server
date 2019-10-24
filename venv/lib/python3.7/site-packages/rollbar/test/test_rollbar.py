import base64
import copy
import json
import mock

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
import unittest

import rollbar
from rollbar.lib import python_major_version, string_types

from rollbar.test import BaseTest

try:
    eval("""
        def _anonymous_tuple_func(x, (a, b), y):
            ret = x + a + b + y
            breakme()
            return ret
    """)
except SyntaxError:
    _anonymous_tuple_func = None


_test_access_token = 'aaaabbbbccccddddeeeeffff00001111'
_default_settings = copy.deepcopy(rollbar.SETTINGS)


class RollbarTest(BaseTest):
    def setUp(self):
        rollbar._initialized = False
        rollbar.SETTINGS = copy.deepcopy(_default_settings)
        rollbar.init(_test_access_token, locals={'enabled': True}, dummy_key='asdf', handler='blocking', timeout=12345)

    def test_merged_settings(self):
        expected = {'enabled': True, 'sizes': rollbar.DEFAULT_LOCALS_SIZES, 'safe_repr': True, 'whitelisted_types': []}
        self.assertDictEqual(rollbar.SETTINGS['locals'], expected)
        self.assertEqual(rollbar.SETTINGS['timeout'], 12345)
        self.assertEqual(rollbar.SETTINGS['dummy_key'], 'asdf')

    def test_default_configuration(self):
        self.assertEqual(rollbar.SETTINGS['access_token'], _test_access_token)
        self.assertEqual(rollbar.SETTINGS['environment'], 'production')

    @mock.patch('rollbar.send_payload')
    def test_disabled(self, send_payload):
        rollbar.SETTINGS['enabled'] = False

        rollbar.report_message('foo')
        try:
            raise Exception('foo')
        except:
            rollbar.report_exc_info()

        self.assertEqual(send_payload.called, False)

    def test_server_data(self):
        server_data = rollbar._build_server_data()

        self.assertIn('host', server_data)
        self.assertIn('argv', server_data)
        self.assertNotIn('branch', server_data)
        self.assertNotIn('root', server_data)

        rollbar.SETTINGS['branch'] = 'master'
        rollbar.SETTINGS['root'] = '/home/test/'

        server_data = rollbar._build_server_data()

        self.assertIn('host', server_data)
        self.assertIn('argv', server_data)
        self.assertEqual(server_data['branch'], 'master')
        self.assertEqual(server_data['root'], '/home/test/')

    def test_wsgi_request_data(self):
        request = {
            'CONTENT_LENGTH': str(len('body body body')),
            'CONTENT_TYPE': '',
            'DOCUMENT_URI': '/api/test',
            'GATEWAY_INTERFACE': 'CGI/1.1',
            'HTTP_CONNECTION': 'close',
            'HTTP_HOST': 'example.com',
            'HTTP_USER_AGENT': 'Agent',
            'PATH_INFO': '/api/test',
            'QUERY_STRING': 'format=json&param1=value1&param2=value2',
            'REMOTE_ADDR': '127.0.0.1',
            'REQUEST_METHOD': 'GET',
            'SCRIPT_NAME': '',
            'SERVER_ADDR': '127.0.0.1',
            'SERVER_NAME': 'example.com',
            'SERVER_PORT': '80',
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'wsgi.input': StringIO('body body body'),
            'wsgi.multiprocess': True,
            'wsgi.multithread': False,
            'wsgi.run_once': False,
            'wsgi.url_scheme': 'http',
            'wsgi.version': (1, 0)
        }
        data = rollbar._build_wsgi_request_data(request)
        self.assertEqual(data['url'], 'http://example.com/api/test?format=json&param1=value1&param2=value2')
        self.assertEqual(data['user_ip'], '127.0.0.1')
        self.assertEqual(data['method'], 'GET')
        self.assertEqual(data['body'], 'body body body')
        self.assertDictEqual(data['GET'], {'format': 'json', 'param1': 'value1', 'param2': 'value2'})
        self.assertDictEqual(data['headers'], {'Connection': 'close', 'Host': 'example.com', 'User-Agent': 'Agent'})

    @mock.patch('rollbar.send_payload')
    def test_report_exception(self, send_payload):

        def _raise():
            try:
                raise Exception('foo')
            except:
                rollbar.report_exc_info()

        _raise()

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])

        self.assertEqual(payload['access_token'], _test_access_token)
        self.assertIn('body', payload['data'])
        self.assertIn('trace', payload['data']['body'])
        self.assertIn('exception', payload['data']['body']['trace'])
        self.assertEqual(payload['data']['body']['trace']['exception']['message'], 'foo')
        self.assertEqual(payload['data']['body']['trace']['exception']['class'], 'Exception')

        self.assertNotIn('args', payload['data']['body']['trace']['frames'][-1])
        self.assertNotIn('kwargs', payload['data']['body']['trace']['frames'][-1])

    @mock.patch('rollbar.send_payload')
    def test_exception_filters(self, send_payload):

        rollbar.SETTINGS['exception_level_filters'] = [
            (OSError, 'ignored'),
            ('rollbar.ApiException', 'ignored'),
            ('bogus.DoesntExist', 'ignored'),
        ]

        def _raise_exception():
            try:
                raise Exception('foo')
            except:
                rollbar.report_exc_info()

        def _raise_os_error():
            try:
                raise OSError('bar')
            except:
                rollbar.report_exc_info()

        def _raise_api_exception():
            try:
                raise rollbar.ApiException('bar')
            except:
                rollbar.report_exc_info()

        _raise_exception()
        self.assertTrue(send_payload.called)

        _raise_os_error()
        self.assertEqual(1, send_payload.call_count)

        _raise_api_exception()
        self.assertEqual(1, send_payload.call_count)


    @mock.patch('rollbar.send_payload')
    def test_report_messsage(self, send_payload):
        rollbar.report_message('foo')

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])

        self.assertEqual(payload['access_token'], _test_access_token)
        self.assertIn('body', payload['data'])
        self.assertIn('message', payload['data']['body'])
        self.assertIn('body', payload['data']['body']['message'])
        self.assertEqual(payload['data']['body']['message']['body'], 'foo')

    @mock.patch('rollbar.send_payload')
    def test_uuid(self, send_payload):
        uuid = rollbar.report_message('foo')

        payload = json.loads(send_payload.call_args[0][0])

        self.assertEqual(payload['data']['uuid'], uuid)

    @mock.patch('rollbar.send_payload')
    def test_report_exc_info_level(self, send_payload):

        try:
            raise Exception('level_error')
        except:
            rollbar.report_exc_info()

        self.assertEqual(send_payload.called, True)
        payload = json.loads(send_payload.call_args[0][0])
        self.assertEqual(payload['data']['level'], 'error')

        try:
            raise Exception('level_info')
        except:
            rollbar.report_exc_info(level='info')

        self.assertEqual(send_payload.called, True)
        payload = json.loads(send_payload.call_args[0][0])
        self.assertEqual(payload['data']['level'], 'info')

        # payload takes precendence over 'level'
        try:
            raise Exception('payload_warn')
        except:
            rollbar.report_exc_info(level='info', payload_data={'level': 'warn'})

        self.assertEqual(send_payload.called, True)
        payload = json.loads(send_payload.call_args[0][0])
        self.assertEqual(payload['data']['level'], 'warn')

    @mock.patch('rollbar.send_payload')
    def test_args_constructor(self, send_payload):

        class tmp(object):
            def __init__(self, arg1):
                self.arg1 = arg1
                foo()

        try:
            t = tmp(33)
        except:
            rollbar.report_exc_info()

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])

        self.assertIn('args', payload['data']['body']['trace']['frames'][-1])
        self.assertEqual(33, payload['data']['body']['trace']['frames'][-1]['args'][1])

    @mock.patch('rollbar.send_payload')
    def test_args_lambda_no_args(self, send_payload):

        _raise = lambda: foo()

        try:
            _raise()
        except:
            rollbar.report_exc_info()

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])

        self.assertNotIn('args', payload['data']['body']['trace']['frames'][-1])
        self.assertNotIn('kwargs', payload['data']['body']['trace']['frames'][-1])

    @mock.patch('rollbar.send_payload')
    def test_args_lambda_with_args(self, send_payload):

        _raise = lambda arg1, arg2: foo(arg1, arg2)

        try:
            _raise('arg1-value', 'arg2-value')
        except:
            rollbar.report_exc_info()

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])

        self.assertIn('args', payload['data']['body']['trace']['frames'][-1])
        self.assertNotIn('kwargs', payload['data']['body']['trace']['frames'][-1])
        self.assertEqual(2, len(payload['data']['body']['trace']['frames'][-1]['args']))
        self.assertEqual('arg1-value', payload['data']['body']['trace']['frames'][-1]['args'][0])
        self.assertEqual('arg2-value', payload['data']['body']['trace']['frames'][-1]['args'][1])

    @mock.patch('rollbar.send_payload')
    def test_args_lambda_with_defaults(self, send_payload):

        _raise = lambda arg1='default': foo(arg1)

        try:
            _raise(arg1='arg1-value')
        except:
            rollbar.report_exc_info()

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])

        self.assertIn('args', payload['data']['body']['trace']['frames'][-1])
        self.assertNotIn('kwargs', payload['data']['body']['trace']['frames'][-1])

        # NOTE(cory): Lambdas are a bit strange. We treat default values for lambda args
        #             as positional.
        self.assertEqual(1, len(payload['data']['body']['trace']['frames'][-1]['args']))
        self.assertEqual('arg1-value', payload['data']['body']['trace']['frames'][-1]['args'][0])

    @mock.patch('rollbar.send_payload')
    def test_args_lambda_with_star_args(self, send_payload):

        _raise = lambda *args: foo(arg1)

        try:
            _raise('arg1-value')
        except:
            rollbar.report_exc_info()

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])

        self.assertIn('args', payload['data']['body']['trace']['frames'][-1])
        self.assertNotIn('kwargs', payload['data']['body']['trace']['frames'][-1])

        self.assertEqual(1, len(payload['data']['body']['trace']['frames'][-1]['args']))
        self.assertEqual('arg1-value', payload['data']['body']['trace']['frames'][-1]['args'][0])

    @mock.patch('rollbar.send_payload')
    def test_args_lambda_with_star_args_and_args(self, send_payload):

        _raise = lambda arg1, *args: foo(arg1)

        try:
            _raise('arg1-value', 1, 2)
        except:
            rollbar.report_exc_info()

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])

        self.assertIn('args', payload['data']['body']['trace']['frames'][-1])
        self.assertNotIn('kwargs', payload['data']['body']['trace']['frames'][-1])

        self.assertEqual(3, len(payload['data']['body']['trace']['frames'][-1]['args']))
        self.assertEqual('arg1-value', payload['data']['body']['trace']['frames'][-1]['args'][0])
        self.assertEqual(1, payload['data']['body']['trace']['frames'][-1]['args'][1])
        self.assertEqual(2, payload['data']['body']['trace']['frames'][-1]['args'][2])

    @mock.patch('rollbar.send_payload')
    def test_args_lambda_with_kwargs(self, send_payload):

        _raise = lambda **args: foo(arg1)

        try:
            _raise(arg1='arg1-value', arg2=2)
        except:
            rollbar.report_exc_info()

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])

        self.assertNotIn('args', payload['data']['body']['trace']['frames'][-1])
        self.assertIn('kwargs', payload['data']['body']['trace']['frames'][-1])

        self.assertEqual(2, len(payload['data']['body']['trace']['frames'][-1]['kwargs']))
        self.assertEqual('arg1-value', payload['data']['body']['trace']['frames'][-1]['kwargs']['arg1'])
        self.assertEqual(2, payload['data']['body']['trace']['frames'][-1]['kwargs']['arg2'])

    @mock.patch('rollbar.send_payload')
    def test_args_lambda_with_kwargs_and_args(self, send_payload):

        _raise = lambda arg1, arg2, **args: foo(arg1)

        try:
            _raise('a1', 'a2', arg3='arg3-value', arg4=2)
        except:
            rollbar.report_exc_info()

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])

        self.assertIn('args', payload['data']['body']['trace']['frames'][-1])
        self.assertIn('kwargs', payload['data']['body']['trace']['frames'][-1])

        self.assertEqual(2, len(payload['data']['body']['trace']['frames'][-1]['args']))
        self.assertEqual(2, len(payload['data']['body']['trace']['frames'][-1]['kwargs']))
        self.assertEqual('a1', payload['data']['body']['trace']['frames'][-1]['args'][0])
        self.assertEqual('a2', payload['data']['body']['trace']['frames'][-1]['args'][1])
        self.assertEqual('arg3-value', payload['data']['body']['trace']['frames'][-1]['kwargs']['arg3'])
        self.assertEqual(2, payload['data']['body']['trace']['frames'][-1]['kwargs']['arg4'])

    @mock.patch('rollbar.send_payload')
    def test_args_lambda_with_kwargs_and_args_and_defaults(self, send_payload):

        _raise = lambda arg1, arg2, arg3='default-value', **args: foo(arg1)

        try:
            _raise('a1', 'a2', arg3='arg3-value', arg4=2)
        except:
            rollbar.report_exc_info()

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])

        self.assertIn('args', payload['data']['body']['trace']['frames'][-1])
        self.assertIn('kwargs', payload['data']['body']['trace']['frames'][-1])

        # NOTE(cory): again, default values are strange for lambdas and we include them as
        #             positional args.
        self.assertEqual(3, len(payload['data']['body']['trace']['frames'][-1]['args']))
        self.assertEqual(1, len(payload['data']['body']['trace']['frames'][-1]['kwargs']))
        self.assertEqual('a1', payload['data']['body']['trace']['frames'][-1]['args'][0])
        self.assertEqual('a2', payload['data']['body']['trace']['frames'][-1]['args'][1])
        self.assertEqual('arg3-value', payload['data']['body']['trace']['frames'][-1]['args'][2])
        self.assertEqual(2, payload['data']['body']['trace']['frames'][-1]['kwargs']['arg4'])

    @mock.patch('rollbar.send_payload')
    def test_args_generators(self, send_payload):

        def _raise(arg1):
            for i in range(2):
                if i > 0:
                    raise Exception()
                else:
                    yield i

        try:
            l = list(_raise('hello world'))
        except:
            rollbar.report_exc_info()

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])

        self.assertIn('args', payload['data']['body']['trace']['frames'][-1])
        self.assertNotIn('kwargs', payload['data']['body']['trace']['frames'][-1])

        self.assertEqual(1, len(payload['data']['body']['trace']['frames'][-1]['args']))
        self.assertEqual('hello world', payload['data']['body']['trace']['frames'][-1]['args'][0])

    @mock.patch('rollbar.send_payload')
    def test_anonymous_tuple_args(self, send_payload):

        # Only run this test on Python versions that support it
        if not _anonymous_tuple_func:
            return

        try:
            _anonymous_tuple_func((1, (2, 3), 4))
        except:
            rollbar.report_exc_info()

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])

        self.assertIn('args', payload['data']['body']['trace']['frames'][-1])
        self.assertNotIn('kwargs', payload['data']['body']['trace']['frames'][-1])

        self.assertEqual(4, len(payload['data']['body']['trace']['frames'][-1]['args']))
        self.assertEqual(1, payload['data']['body']['trace']['frames'][-1]['args'][0])
        self.assertEqual(2, payload['data']['body']['trace']['frames'][-1]['args'][1])
        self.assertEqual(3, payload['data']['body']['trace']['frames'][-1]['args'][2])
        self.assertEqual(4, payload['data']['body']['trace']['frames'][-1]['args'][3])
        self.assertEqual(10, payload['data']['body']['trace']['frames'][-1]['locals']['ret'])

    @mock.patch('rollbar.send_payload')
    def test_scrub_kwargs(self, send_payload):

        def _raise(password='sensitive', clear='text'):
            raise Exception()

        try:
            _raise()
        except:
            rollbar.report_exc_info()

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])

        self.assertNotIn('args', payload['data']['body']['trace']['frames'][-1])
        self.assertIn('kwargs', payload['data']['body']['trace']['frames'][-1])

        self.assertEqual(2, len(payload['data']['body']['trace']['frames'][-1]['kwargs']))
        self.assertRegex(payload['data']['body']['trace']['frames'][-1]['kwargs']['password'], '\*+')
        self.assertEqual('text', payload['data']['body']['trace']['frames'][-1]['kwargs']['clear'])

    @mock.patch('rollbar.send_payload')
    def test_scrub_locals(self, send_payload):
        invalid_b64 = b'CuX2JKuXuLVtJ6l1s7DeeQ=='
        invalid = base64.b64decode(invalid_b64)

        def _raise():
            # Make sure that the _invalid local variable makes its
            # way into the payload even if its value cannot be serialized
            # properly.
            _invalid = invalid

            # Make sure the Password field gets scrubbed even though its
            # original value could not be serialized properly.
            Password = invalid

            password = 'sensitive'
            raise Exception((_invalid, Password, password))

        try:
            _raise()
        except:
            rollbar.report_exc_info()

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])

        self.assertRegex(payload['data']['body']['trace']['frames'][-1]['locals']['password'], '\*+')
        self.assertRegex(payload['data']['body']['trace']['frames'][-1]['locals']['Password'], '\*+')
        self.assertIn('_invalid', payload['data']['body']['trace']['frames'][-1]['locals'])

        binary_type_name = 'str' if python_major_version() < 3 else 'bytes'
        undecodable_message = '<Undecodable type:(%s) base64:(%s)>' % (binary_type_name, base64.b64encode(invalid).decode('ascii'))
        self.assertEqual(undecodable_message, payload['data']['body']['trace']['frames'][-1]['locals']['_invalid'])

    @mock.patch('rollbar.send_payload')
    def test_scrub_nans(self, send_payload):
        def _raise():
            infinity = float('Inf')
            not_a_number = float('NaN')
            raise Exception()

        try:
            _raise()
        except:
            rollbar.report_exc_info()

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])

        self.assertEqual('Infinity', payload['data']['body']['trace']['frames'][-1]['locals']['infinity'])
        self.assertEqual('NaN', payload['data']['body']['trace']['frames'][-1]['locals']['not_a_number'])

    @mock.patch('rollbar.send_payload')
    def test_scrub_self_referencing(self, send_payload):
        def _raise(obj):
            raise Exception()

        try:
            obj = {}
            obj['child'] = {
                'parent': obj
            }

            # NOTE(cory): We copy the dict here so that we don't produce a circular reference
            # from the _rase() args.
            _raise(dict(obj))
        except:
            rollbar.report_exc_info()

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])

        self.assertTrue(
            (isinstance(payload['data']['body']['trace']['frames'][-1]['locals']['obj'], dict) and
             'child' in payload['data']['body']['trace']['frames'][-1]['locals']['obj'])

             or

            (isinstance(payload['data']['body']['trace']['frames'][-1]['locals']['obj'], string_types) and
             payload['data']['body']['trace']['frames'][-1]['locals']['obj'].startswith('<CircularReference'))
        )

    @mock.patch('rollbar.send_payload')
    def test_scrub_local_ref(self, send_payload):
        """
        NOTE(cory): This test checks to make sure that we do not scrub a local variable that is a reference
                    to a parameter that is scrubbed.
                    Ideally we would be able to scrub 'copy' as well since we know that it has the same
                    value as a field that was scrubbed.
        """
        def _raise(password='sensitive'):
            copy = password
            raise Exception()

        try:
            _raise()
        except:
            rollbar.report_exc_info()

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])

        self.assertEqual('sensitive', payload['data']['body']['trace']['frames'][-1]['locals']['copy'])

    @mock.patch('rollbar.send_payload')
    def test_large_arg_val(self, send_payload):

        def _raise(large):
            raise Exception()

        try:
            large = ''.join(['#'] * 200)
            _raise(large)
        except:
            rollbar.report_exc_info()

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])

        self.assertIn('args', payload['data']['body']['trace']['frames'][-1])
        self.assertNotIn('kwargs', payload['data']['body']['trace']['frames'][-1])
        self.assertEqual(1, len(payload['data']['body']['trace']['frames'][-1]['args']))

        self.assertEqual("'###############################################...################################################'",
                         payload['data']['body']['trace']['frames'][-1]['args'][0])


    @mock.patch('rollbar.send_payload')
    def test_long_list_arg_val(self, send_payload):

        def _raise(large):
            raise Exception()

        try:
            xlarge = ['hi' for _ in range(30)]
            # NOTE(cory): We copy the list here so that the local variables from
            # this frame are not referenced directly by the frame from _raise()
            # call above. If we didn't copy this list, Rollbar would report a
            # circular reference for the args on _raise().
            _raise([str(x) for x in xlarge])
        except:
            rollbar.report_exc_info()

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])

        self.assertIn('args', payload['data']['body']['trace']['frames'][-1])
        self.assertNotIn('kwargs', payload['data']['body']['trace']['frames'][-1])

        self.assertEqual(1, len(payload['data']['body']['trace']['frames'][-1]['args']))

        self.assertTrue(
            ("['hi', 'hi', 'hi', 'hi', 'hi', 'hi', 'hi', 'hi', 'hi', 'hi', ...]" ==
                payload['data']['body']['trace']['frames'][-1]['args'][0])

            or

            ("['hi', 'hi', 'hi', 'hi', 'hi', 'hi', 'hi', 'hi', 'hi', 'hi', ...]" ==
                    payload['data']['body']['trace']['frames'][0]['locals']['xlarge']))


    @mock.patch('rollbar.send_payload')
    def test_last_frame_has_locals(self, send_payload):

        def _raise():
            some_var = 'some value'
            raise Exception()

        try:
            _raise()
        except:
            rollbar.report_exc_info()

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])

        self.assertNotIn('args', payload['data']['body']['trace']['frames'][-1])
        self.assertNotIn('kwargs', payload['data']['body']['trace']['frames'][-1])

        self.assertIn('locals', payload['data']['body']['trace']['frames'][-1])
        self.assertIn('some_var', payload['data']['body']['trace']['frames'][-1]['locals'])
        self.assertEqual("some value",
                         payload['data']['body']['trace']['frames'][-1]['locals']['some_var'])


    @mock.patch('rollbar.send_payload')
    def test_all_project_frames_have_locals(self, send_payload):

        prev_root = rollbar.SETTINGS['root']
        rollbar.SETTINGS['root'] = __file__.rstrip('pyc')
        try:
            step1()
        except:
            rollbar.report_exc_info()
        finally:
            rollbar.SETTINGS['root'] = prev_root

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])
        for frame in payload['data']['body']['trace']['frames']:
            self.assertIn('locals', frame)


    @mock.patch('rollbar.send_payload')
    def test_only_last_frame_has_locals(self, send_payload):

        prev_root = rollbar.SETTINGS['root']
        rollbar.SETTINGS['root'] = 'dummy'
        try:
            step1()
        except:
            rollbar.report_exc_info()
        finally:
            rollbar.SETTINGS['root'] = prev_root

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])

        num_frames = len(payload['data']['body']['trace']['frames'])
        for i, frame in enumerate(payload['data']['body']['trace']['frames']):
            if i < num_frames - 1:
                self.assertNotIn('locals', frame)
            else:
                self.assertIn('locals', frame)


    @mock.patch('rollbar.send_payload')
    def test_modify_arg(self, send_payload):
        # Record locals for all frames
        prev_root = rollbar.SETTINGS['root']
        rollbar.SETTINGS['root'] = __file__.rstrip('pyc')
        try:
            called_with('original value')
        except:
            rollbar.report_exc_info()
        finally:
            rollbar.SETTINGS['root'] = prev_root

        self.assertEqual(send_payload.called, True)

        payload = json.loads(send_payload.call_args[0][0])

        frames = payload['data']['body']['trace']['frames']
        called_with_frame = frames[1]

        self.assertEqual('changed', called_with_frame['args'][0])

    @mock.patch('rollbar.send_payload')
    def test_unicode_exc_info(self, send_payload):
        message = '\u221a'

        try:
            raise Exception(message)
        except:
            rollbar.report_exc_info()

        self.assertEqual(send_payload.called, True)
        payload = json.loads(send_payload.call_args[0][0])
        self.assertEqual(payload['data']['body']['trace']['exception']['message'], message)

    @mock.patch('requests.post', side_effect=lambda *args, **kw: MockResponse({'status': 'OK'}, 200))
    def test_serialize_and_send_payload(self, post=None):
        invalid_b64 = b'CuX2JKuXuLVtJ6l1s7DeeQ=='
        invalid = base64.b64decode(invalid_b64)

        def _raise():
            # Make sure that the _invalid local variable makes its
            # way into the payload even if its value cannot be serialized
            # properly.
            _invalid = invalid

            # Make sure the Password field gets scrubbed even though its
            # original value could not be serialized properly.
            Password = invalid

            password = 'sensitive'
            raise Exception('bug bug')

        try:
            _raise()
        except:
            rollbar.report_exc_info()

        self.assertEqual(post.called, True)
        payload_data = post.call_args[1]['data']
        self.assertIsInstance(payload_data, str)
        self.assertIn('bug bug', payload_data)

        try:
            json.loads(post.call_args[1]['data'])
        except:
            self.assertTrue(False)

    def test_scrub_webob_request_data(self):
        rollbar._initialized = False
        rollbar.init(_test_access_token, locals={'enabled': True}, dummy_key='asdf', handler='blocking', timeout=12345,
            scrub_fields=rollbar.SETTINGS['scrub_fields'] + ['token', 'secret', 'cookies', 'authorization'])

        import webob
        request = webob.Request.blank('/the/path?q=hello&password=hunter2',
                                      base_url='http://example.com',
                                      headers={
                                          'X-Real-Ip': '5.6.7.8',
                                          'Cookies': 'name=value; password=hash;',
                                          'Authorization': 'I am from NSA'
                                      },
                                      POST='foo=bar&confirm_password=hunter3&token=secret')

        unscrubbed = rollbar._build_webob_request_data(request)
        self.assertEqual(unscrubbed['url'], 'http://example.com/the/path?q=hello&password=hunter2')
        self.assertEqual(unscrubbed['user_ip'], '5.6.7.8')
        self.assertDictEqual(unscrubbed['GET'], {'q': 'hello', 'password': 'hunter2'})
        self.assertDictEqual(unscrubbed['POST'], {'foo': 'bar', 'confirm_password': 'hunter3', 'token': 'secret'})
        self.assertEqual('5.6.7.8', unscrubbed['headers']['X-Real-Ip'])
        self.assertEqual('name=value; password=hash;', unscrubbed['headers']['Cookies'])
        self.assertEqual('I am from NSA', unscrubbed['headers']['Authorization'])

        scrubbed = rollbar._transform(unscrubbed)
        self.assertRegex(scrubbed['url'], r'http://example.com/the/path\?(q=hello&password=-+)|(password=-+&q=hello)')

        self.assertEqual(scrubbed['GET']['q'], 'hello')
        self.assertRegex(scrubbed['GET']['password'], r'\*+')

        self.assertEqual(scrubbed['POST']['foo'], 'bar')
        self.assertRegex(scrubbed['POST']['confirm_password'], r'\*+')
        self.assertRegex(scrubbed['POST']['token'], r'\*+')

        self.assertEqual('5.6.7.8', scrubbed['headers']['X-Real-Ip'])

        self.assertRegex(scrubbed['headers']['Cookies'], r'\*+')
        self.assertRegex(scrubbed['headers']['Authorization'], r'\*+')


### Helpers

def step1():
    val1 = 1
    step2()


def step2():
    val2 = 2
    raise Exception()


def called_with(arg1):
    arg1 = 'changed'
    step1()


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    @property
    def content(self):
        return json.dumps(self.json_data)

    def json(self):
        return self.json_data


if __name__ == '__main__':
    unittest.main()
