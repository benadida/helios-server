"""
Unit Tests for Auth Systems
"""

import unittest
import models

from django.db import IntegrityError, transaction

from auth_systems import AUTH_SYSTEMS

class UserTests(unittest.TestCase):

    def setUp(self):
        pass

    def test_unique_users(self):
        """
        there should not be two users with the same user_type and user_id
        """
        for auth_system, auth_system_module in AUTH_SYSTEMS.iteritems():
            models.User.objects.create(user_type = auth_system, user_id = 'foobar', info={'name':'Foo Bar'})
            
            def double_insert():
                models.User.objects.create(user_type = auth_system, user_id = 'foobar', info={'name': 'Foo2 Bar'})
                
            self.assertRaises(IntegrityError, double_insert)
            transaction.rollback()

    def test_create_or_update(self):
        """
        shouldn't create two users, and should reset the password
        """
        for auth_system, auth_system_module in AUTH_SYSTEMS.iteritems():
            u = models.User.update_or_create(user_type = auth_system, user_id = 'foobar_cou', info={'name':'Foo Bar'})

            def double_update_or_create():
                new_name = 'Foo2 Bar'
                u2 = models.User.update_or_create(user_type = auth_system, user_id = 'foobar_cou', info={'name': new_name})

                self.assertEquals(u.id, u2.id)
                self.assertEquals(u2.info['name'], new_name)


    def test_status_update(self):
        """
        check that a user set up with status update ability reports it as such,
        and otherwise does not report it
        """
        for auth_system, auth_system_module in AUTH_SYSTEMS.iteritems():
            u = models.User.update_or_create(user_type = auth_system, user_id = 'foobar_status_update', info={'name':'Foo Bar Status Update'})

            if hasattr(auth_system_module, 'send_message'):
                self.assertNotEquals(u.update_status_template, None)
            else:
                self.assertEquals(u.update_status_template, None)

    def test_eligibility(self):
        """
        test that users are reported as eligible for something

        FIXME: also test constraints on eligibility
        """
        for auth_system, auth_system_module in AUTH_SYSTEMS.iteritems():
            u = models.User.update_or_create(user_type = auth_system, user_id = 'foobar_status_update', info={'name':'Foo Bar Status Update'})

            self.assertTrue(u.is_eligible_for({'auth_system': auth_system}))

    def test_eq(self):
        for auth_system, auth_system_module in AUTH_SYSTEMS.iteritems():
            u = models.User.update_or_create(user_type = auth_system, user_id = 'foobar_eq', info={'name':'Foo Bar Status Update'})
            u2 = models.User.update_or_create(user_type = auth_system, user_id = 'foobar_eq', info={'name':'Foo Bar Status Update'})

            self.assertEquals(u, u2)
