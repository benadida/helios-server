"""
Tests for Twisted instrumentation
"""

import json
import sys

import mock
import rollbar

# access token for https://rollbar.com/rollbar/pyrollbar
TOKEN = '92c10f5616944b81a2e6f3c6493a0ec2'

# Twisted hasn't been fully ported to Python 3 yet, so don't test there.
ALLOWED_PYTHON_VERSION = not sys.version_info[0] == 3
try:
    from twisted.test import proto_helpers
    from twisted.trial import unittest
    from twisted.internet import protocol
    from twisted.python import log

    TWISTED_INSTALLED = True
except ImportError:
    TWISTED_INSTALLED = False

if ALLOWED_PYTHON_VERSION and TWISTED_INSTALLED:
    class SquareProtocol(protocol.Protocol):
        def dataReceived(self, data):
            try:
                number = int(data)
            except ValueError:
                log.err()
                self.transport.write('error')
            else:
                self.transport.write(str(number**2))

    class SquareFactory(protocol.Factory):
        protocol = SquareProtocol

    class TwistedTest(unittest.TestCase):
        def setUp(self):
            rollbar.init(TOKEN, 'twisted-test')
            factory = SquareFactory()
            self.proto = factory.buildProtocol(('127.0.0.1', 0))
            self.tr = proto_helpers.StringTransport()
            self.proto.makeConnection(self.tr)

        @mock.patch('rollbar.send_payload')
        def test_base_case(self, send_payload):
            self.proto.dataReceived('8')
            self.assertEqual(int(self.tr.value()), 64)

            self.assertEqual(send_payload.called, False)

        @mock.patch('rollbar.send_payload')
        def test_caught_exception(self, send_payload):
            self.proto.dataReceived('rollbar')
            self.assertEqual(self.tr.value(), "error")
            errors = self.flushLoggedErrors(ValueError)
            self.assertEqual(len(errors), 1)

            self.assertEqual(send_payload.called, True)
            payload = json.loads(send_payload.call_args[0][0])
            data = payload['data']

            self.assertIn('body', data)
            self.assertEqual(data['body']['trace']['exception']['class'],
                             'ValueError')
            self.assertEqual(data['body']['trace']['exception']['message'],
                             "invalid literal for int() with base 10: 'rollbar'")

        # XXX not able to test uncaught exceptions for some reason
        # @mock.patch('rollbar.send_payload')
        # def test_uncaught_exception(self, send_payload):
        #     self.proto.dataReceived([8, 9])
        #     self.assertEqual(self.tr.value(), "error")
        #     errors = self.flushLoggedErrors(TypeError)
        #     self.assertEqual(len(errors), 1)
        #
        #     self.assertEqual(send_payload.called, True)
        #     payload = json.loads(send_payload.call_args[0][0])
        #     data = payload['data']
        #
        #     self.assertIn('body', data)
        #     self.assertEqual(data['body']['trace']['exception']['class'],
        #                      'TypeError')
        #     self.assertEqual(data['body']['trace']['exception']['message'],
        #                      "int() argument must be a string or a number, not 'list'")
