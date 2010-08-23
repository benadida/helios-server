"""
Unit Tests for Helios
"""

import unittest
import models

from auth import models as auth_models

from django.db import IntegrityError, transaction

from django.test.client import Client
from django.test import TestCase

from django.core import mail

class ElectionModelTests(unittest.TestCase):

    def setUp(self):
        self.user = auth_models.User.objects.create(user_id='foobar', name='Foo Bar', user_type='password', info={})

    def test_create_election(self):
        self.election, created_p = models.Election.get_or_create(
            short_name='demo',
            name='Demo Election',
            description='Demo Election Description',
            admin=self.user)

        # election should be created
        self.assertTrue(created_p)

        # should have a creation time
        self.assertNotEquals(self.election.created_at, None)
        #self.assert

