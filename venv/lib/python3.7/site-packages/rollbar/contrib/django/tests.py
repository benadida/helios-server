"""
Unit tests
"""
from django.test import TestCase
from django.conf import settings

class BasicTests(TestCase):
    def test_configuration(self):
        """
        Test that the configuration is sane.
        """
        self.assertTrue('ROLLBAR' in dir(settings),
            msg='The ROLLBAR setting is not present.')
        self.assertTrue(settings.ROLLBAR.get('access_token'),
            msg='The ROLLBAR["access_token"] setting is blank.')
        
