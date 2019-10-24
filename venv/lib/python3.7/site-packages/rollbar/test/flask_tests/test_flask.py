"""
Tests for Flask instrumentation
"""

import json
import sys
import os

import mock
import rollbar

from rollbar.test import BaseTest

# access token for https://rollbar.com/rollbar/pyrollbar
TOKEN = '92c10f5616944b81a2e6f3c6493a0ec2'

# Flask doesn't work on python 3.2, so don't test there.
ALLOWED_PYTHON_VERSION = not (sys.version_info[0] == 3 and sys.version_info[1] == 2)

try:
    import flask
    FLASK_INSTALLED = True
except ImportError:
    FLASK_INSTALLED = False


def create_app():
    from flask import Flask, Request, got_request_exception
    import rollbar.contrib.flask
    app = Flask(__name__)

    @app.route('/')
    def index():
        return 'Index page'

    @app.route('/cause_error', methods=['GET', 'POST'])
    def cause_error():
        raise Exception("Uh oh")

    @app.before_first_request
    def init_rollbar():
        rollbar.init(TOKEN, 'flasktest',
                     root=os.path.dirname(os.path.realpath(__file__)),
                     allow_logging_basic_config=True)
        got_request_exception.connect(rollbar.contrib.flask.report_exception, app)

    class CustomRequest(Request):
        @property
        def rollbar_person(self):
            return {'id': '123', 'username': 'testuser', 'email': 'test@example.com'}

    app.request_class = CustomRequest

    return app

if ALLOWED_PYTHON_VERSION and FLASK_INSTALLED:
    class FlaskTest(BaseTest):
        def setUp(self):
            super(FlaskTest, self).setUp()
            self.app = create_app()
            self.client = self.app.test_client()

        def test_index(self):
            resp = self.client.get('/')
            self.assertEqual(resp.status_code, 200)

        def assertStringEqual(self, left, right):
            if sys.version_info[0] > 2:
                if hasattr(left, 'decode'):
                    left = left.decode('ascii')
                if hasattr(right, 'decode'):
                    right = right.decode('ascii')

                return self.assertEqual(left, right)
            else:
                return self.assertEqual(left, right)

        @mock.patch('rollbar.send_payload')
        def test_uncaught(self, send_payload):
            resp = self.client.get('/cause_error?foo=bar',
                headers={'X-Real-Ip': '1.2.3.4', 'User-Agent': 'Flask Test'})
            self.assertEqual(resp.status_code, 500)

            self.assertEqual(send_payload.called, True)
            payload = json.loads(send_payload.call_args[0][0])
            data = payload['data']

            self.assertIn('body', data)
            self.assertEqual(data['body']['trace']['exception']['class'], 'Exception')
            self.assertStringEqual(data['body']['trace']['exception']['message'], 'Uh oh')

            self.assertIn('person', data)
            self.assertDictEqual(data['person'],
                {'id': '123', 'username': 'testuser', 'email': 'test@example.com'})

            self.assertIn('request', data)
            self.assertEqual(data['request']['url'], 'http://localhost/cause_error?foo=bar')
            self.assertDictEqual(data['request']['GET'], {'foo': ['bar']})
            self.assertEqual(data['request']['user_ip'], '1.2.3.4')
            self.assertEqual(data['request']['method'], 'GET')
            self.assertEqual(data['request']['headers']['User-Agent'], 'Flask Test')

        @mock.patch('rollbar.send_payload')
        def test_uncaught_json_request(self, send_payload):
            json_body = {"hello": "world"}
            json_body_str = json.dumps(json_body)
            resp = self.client.post('/cause_error', data=json_body_str,
                headers={'Content-Type': 'application/json', 'X-Forwarded-For': '5.6.7.8'})

            self.assertEqual(resp.status_code, 500)

            self.assertEqual(send_payload.called, True)
            payload = json.loads(send_payload.call_args[0][0])
            data = payload['data']

            self.assertIn('body', data)
            self.assertEqual(data['body']['trace']['exception']['class'], 'Exception')
            self.assertStringEqual(data['body']['trace']['exception']['message'], 'Uh oh')

            self.assertIn('person', data)
            self.assertDictEqual(data['person'],
                {'id': '123', 'username': 'testuser', 'email': 'test@example.com'})

            self.assertIn('request', data)
            self.assertEqual(data['request']['url'], 'http://localhost/cause_error')
            self.assertEqual(data['request']['body'], json_body)
            self.assertEqual(data['request']['user_ip'], '5.6.7.8')
            self.assertEqual(data['request']['method'], 'POST')
