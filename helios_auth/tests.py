# -*- coding: utf-8 -*-
"""
Unit Tests for Auth Systems
"""

import unittest
import models

from django.db import IntegrityError, transaction

from django.test.client import Client
from django.test import TestCase

from django.core import mail

from auth_systems import AUTH_SYSTEMS
from helios_auth import ENABLED_AUTH_SYSTEMS

class UserModelTests(unittest.TestCase):

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


    def test_can_create_election(self):
        """
        check that auth systems have the can_create_election call and that it's true for the common ones
        """
        for auth_system, auth_system_module in AUTH_SYSTEMS.iteritems():
            assert(hasattr(auth_system_module, 'can_create_election'))
            if auth_system != 'clever':
                assert(auth_system_module.can_create_election('foobar', {}))


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


import views
import auth_systems.password as password_views
from django.core.urlresolvers import reverse

# FIXME: login CSRF should make these tests more complicated
# and should be tested for

class UserBlackboxTests(TestCase):

    def setUp(self):
        # create a bogus user
        self.test_user = models.User.objects.create(user_type='password',user_id='foobar-test@adida.net',name="Foobar User", info={'password':'foobaz'})

    def test_password_login(self):
        ## we can't test this anymore until it's election specific
        pass

        # get to the login page
        # login_page_response = self.client.get(reverse(views.start, kwargs={'system_name':'password'}), follow=True)

        # log in and follow all redirects
        # response = self.client.post(reverse(password_views.password_login_view), {'username' : 'foobar_user', 'password': 'foobaz'}, follow=True)

        # self.assertContains(response, "logged in as")
        # self.assertContains(response, "Foobar User")

    def test_logout(self):
        response = self.client.post(reverse(views.logout), follow=True)

        self.assertContains(response, "not logged in")
        self.assertNotContains(response, "Foobar User")

    def test_email(self):
        """using the test email backend"""
        self.test_user.send_message("testing subject", "testing body")

        self.assertEquals(len(mail.outbox), 1)
        self.assertEquals(mail.outbox[0].subject, "testing subject")
        self.assertEquals(mail.outbox[0].to[0], "\"Foobar User\" <foobar-test@adida.net>")


'''
    tests for LDAP auth module.
    Much of the code below was get or inspired on django-auth-ldap package.
    See site-packages/django_ldap_auth/tests.py
'''
import ldap

import auth_systems.ldapauth as ldap_views
from mockldap import MockLdap
from django_auth_ldap.backend import LDAPSettings
from django_auth_ldap.config import LDAPSearch
from helios_auth.auth_systems.ldapbackend.backend import CustomLDAPBackend
try:
    from django.test.utils import override_settings
except ImportError:
    override_settings = lambda *args, **kwargs: (lambda v: v)


class TestSettings(LDAPSettings):
    """
    A replacement for backend.LDAPSettings that does not load settings
    from django.conf.
    """
    def __init__(self, **kwargs):
        for name, default in self.defaults.items():
            value = kwargs.get(name, default)
            setattr(self, name, value)


class LDAPAuthTests(TestCase):
    """
    These tests uses mockldap 0.2.7 https://pypi.python.org/pypi/mockldap/
    """

    top = ("o=test", {"o": "test"})
    people = ("ou=people,o=test", {"ou": "people"})
    groups = ("ou=groups,o=test", {"ou": "groups"})

    alice = ("uid=alice,ou=people,o=test", {
        "uid": ["alice"],
        "objectClass": ["person", "organizationalPerson", "inetOrgPerson", "posixAccount"],
        "userPassword": ["password"],
        "uidNumber": ["1000"],
        "gidNumber": ["1000"],
        "givenName": ["Alice"],
        "sn": ["Adams"],
        "mail": ["alice@example.com"]
    })
    bob = ("uid=bob,ou=people,o=test", {
        "uid": ["bob"],
        "objectClass": ["person", "organizationalPerson", "inetOrgPerson", "posixAccount"],
        "userPassword": ["password"],
        "uidNumber": ["1001"],
        "gidNumber": ["50"],
        "givenName": ["Robert"],
        "sn": ["Barker"],
        "mail": ["bob@example.com"]
    })
    john = ("uid=john,ou=people,o=test", {
        "uid": ["john"],
        "objectClass": ["person", "organizationalPerson", "inetOrgPerson", "posixAccount"],
        "userPassword": ["password"],
        "uidNumber": ["1002"],
        "gidNumber": ["60"],
        "givenName": ["Robert"],
        "sn": ["Doe"]
    })

    directory = dict([top, people, groups, alice, bob, john])

    def _init_settings(self, **kwargs):
        self.backend.settings = TestSettings(**kwargs)

    @classmethod
    def setUpClass(cls):
        cls.mockldap = MockLdap(cls.directory)

    @classmethod
    def tearDownClass(cls):
        del cls.mockldap

    def setUp(self):
        self.mockldap.start()
        self.ldapobj = self.mockldap['ldap://localhost']

        self.backend = CustomLDAPBackend()
        self.backend.ldap  # Force global configuration

    def tearDown(self):
        self.mockldap.stop()
        del self.ldapobj

    def test_backend_login(self):
        """ Test authentication usign correct username/password """
        if 'ldap' in ENABLED_AUTH_SYSTEMS:
            self._init_settings(
                BIND_DN='uid=bob,ou=people,o=test',
                BIND_PASSWORD='password',
                USER_SEARCH=LDAPSearch(
                    "ou=people,o=test", ldap.SCOPE_SUBTREE, '(uid=%(user)s)'
                )
            )
            user = self.backend.authenticate(username='alice', password='password')
            self.assertTrue(user is not None)

    def test_backend_bad_login(self):
        """ Test authentication using incorrect username/password"""
        if 'ldap' in ENABLED_AUTH_SYSTEMS:
            self._init_settings(
                BIND_DN='uid=bob,ou=people,o=test',
                BIND_PASSWORD='password',
                USER_SEARCH=LDAPSearch(
                    "ou=people,o=test", ldap.SCOPE_SUBTREE, '(uid=%(user)s)'
                )
            )
            user = self.backend.authenticate(username='maria', password='password')
            self.assertTrue(user is None)

    @override_settings(AUTH_LDAP_BIND_DN='uid=bob,ou=people,o=test',
        AUTH_LDAP_BIND_PASSWORD='password',AUTH_LDAP_USER_SEARCH=LDAPSearch(
            "ou=people,o=test", ldap.SCOPE_SUBTREE, '(uid=%(user)s)'
        )
    )
    def test_ldap_view_login_with_bind_credentials(self):
        """ Test if authenticates using the auth system login view """
        if 'ldap' in ENABLED_AUTH_SYSTEMS:
            response = self.client.post(reverse(ldap_views.ldap_login_view), {
                'username' : 'bob',
                'password': 'password'
            }, follow=True)
            self.assertEqual(self.client.session['user']['name'], 'Robert Barker')
            self.assertEqual(self.client.session['user']['type'], 'ldap')
            self.assertEqual(self.client.session['user']['info']['email'],'bob@example.com')

    @override_settings(AUTH_LDAP_BIND_DN='uid=bob,ou=people,o=test',
        AUTH_LDAP_BIND_PASSWORD='password',AUTH_LDAP_USER_SEARCH=LDAPSearch(
            "ou=people,o=test", ldap.SCOPE_SUBTREE, '(uid=%(user)s)'
        )
    )
    def test_ldap_view_login_with_bad_password(self):
        """ Test if given a wrong password the user can't login """
        if 'ldap' in ENABLED_AUTH_SYSTEMS:
            response = self.client.post(reverse(ldap_views.ldap_login_view), {
                'username' : 'john',
                'password': 'passworddd'
            }, follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertFalse(self.client.session.has_key('user'))

    def test_ldap_view_login_anonymous_bind(self):
        """
        Test anonymous search/bind
        See https://pythonhosted.org/django-auth-ldap/authentication.html#search-bind
        """
        self._init_settings(
            BIND_PASSWORD='',
            USER_ATTR_MAP={'first_name': 'givenName', 'last_name': 'sn','email':'mail'},
            USER_SEARCH=LDAPSearch(
                "ou=people,o=test", ldap.SCOPE_SUBTREE, '(uid=%(user)s)'
            )
        )
        user = self.backend.authenticate(username='alice', password='password')
        self.assertEqual(user.username, 'alice')
        self.assertEqual(user.first_name, 'Alice')
        self.assertEqual(user.last_name, 'Adams')
        self.assertEqual(user.email,'alice@example.com')

    def test_ldap_bind_as_user(self):
        """
        Test direct bind
        See https://pythonhosted.org/django-auth-ldap/authentication.html#direct-bind
        """
        self._init_settings(
            USER_DN_TEMPLATE='uid=%(user)s,ou=people,o=test',
            USER_ATTR_MAP={'first_name': 'givenName', 'last_name': 'sn','email':'mail'},
            BIND_AS_AUTHENTICATING_USER=True,
            USER_SEARCH=LDAPSearch(
                "ou=people,o=test", ldap.SCOPE_SUBTREE, '(uid=%(user)s)'
            )
        )
        user = self.backend.authenticate(username='alice', password='password')
        self.assertEqual(user.username, 'alice')
        self.assertEqual(user.first_name, 'Alice')
        self.assertEqual(user.last_name, 'Adams')
        self.assertEqual(user.email,'alice@example.com')

    def test_logout(self):
        """ test logging out using the auth system logout view """
        if 'ldap' in ENABLED_AUTH_SYSTEMS:
            response = self.client.post(reverse(views.logout), follow=True)
            self.assertContains(response, "not logged in")
            self.assertNotContains(response, "alice")
