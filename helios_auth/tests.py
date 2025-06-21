"""
Unit Tests for Auth Systems
"""

import unittest

from django.core import mail
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from . import models, views
from .auth_systems import AUTH_SYSTEMS, password as password_views

# Import devlogin for testing if available
try:
    from .auth_systems import devlogin
except ImportError:
    devlogin = None


class UserModelTests(unittest.TestCase):

    def setUp(self):
        pass

    def test_unique_users(self):
        """
        there should not be two users with the same user_type and user_id
        """
        for auth_system, auth_system_module in AUTH_SYSTEMS.items():
            models.User.objects.create(user_type = auth_system, user_id = 'foobar', info={'name':'Foo Bar'})
            
            def double_insert():
                models.User.objects.create(user_type = auth_system, user_id = 'foobar', info={'name': 'Foo2 Bar'})
                
            self.assertRaises(IntegrityError, double_insert)
            transaction.rollback()

    def test_create_or_update(self):
        """
        shouldn't create two users, and should reset the password
        """
        for auth_system, auth_system_module in AUTH_SYSTEMS.items():
            u = models.User.update_or_create(user_type = auth_system, user_id = 'foobar_cou', info={'name':'Foo Bar'})

            def double_update_or_create():
                new_name = 'Foo2 Bar'
                u2 = models.User.update_or_create(user_type = auth_system, user_id = 'foobar_cou', info={'name': new_name})

                self.assertEqual(u.id, u2.id)
                self.assertEqual(u2.info['name'], new_name)


    def test_can_create_election(self):
        """
        check that auth systems have the can_create_election call and that it's true for the common ones
        """
        for auth_system, auth_system_module in AUTH_SYSTEMS.items():
            assert(hasattr(auth_system_module, 'can_create_election'))
            if auth_system != 'clever':
                assert(auth_system_module.can_create_election('foobar', {}))
        

    def test_status_update(self):
        """
        check that a user set up with status update ability reports it as such,
        and otherwise does not report it
        """
        for auth_system, auth_system_module in AUTH_SYSTEMS.items():
            u = models.User.update_or_create(user_type = auth_system, user_id = 'foobar_status_update', info={'name':'Foo Bar Status Update'})

            if hasattr(auth_system_module, 'send_message'):
                self.assertNotEqual(u.update_status_template, None)
            else:
                self.assertEqual(u.update_status_template, None)

    def test_eligibility(self):
        """
        test that users are reported as eligible for something

        FIXME: also test constraints on eligibility
        """
        for auth_system, auth_system_module in AUTH_SYSTEMS.items():
            u = models.User.update_or_create(user_type = auth_system, user_id = 'foobar_status_update', info={'name':'Foo Bar Status Update'})

            self.assertTrue(u.is_eligible_for({'auth_system': auth_system}))

    def test_eq(self):
        for auth_system, auth_system_module in AUTH_SYSTEMS.items():
            u = models.User.update_or_create(user_type = auth_system, user_id = 'foobar_eq', info={'name':'Foo Bar Status Update'})
            u2 = models.User.update_or_create(user_type = auth_system, user_id = 'foobar_eq', info={'name':'Foo Bar Status Update'})

            self.assertEqual(u, u2)


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
        response = self.client.post(reverse("auth@logout"), follow=True)
        
        self.assertContains(response, "not logged in")
        self.assertNotContains(response, "Foobar User")

    def test_email(self):
        """using the test email backend"""
        self.test_user.send_message("testing subject", "testing body")

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "testing subject")
        self.assertEqual(mail.outbox[0].to[0], "\"Foobar User\" <foobar-test@adida.net>")
        
# LDAP auth tests
from .auth_systems import ldapauth as ldap_views
class LDAPAuthTests(TestCase):
    """
    These tests relies on OnLine LDAP Test Server, provided by forum Systems:
    http://www.forumsys.com/tutorials/integration-how-to/ldap/online-ldap-test-server/
    """

    def setUp(self):
        """ set up necessary django-auth-ldap settings """
        self.password = 'password'
        self.username = 'euclid'

    def test_backend_login(self):
        """ test if authenticates using the backend """
        from helios_auth.auth_systems.ldapbackend import backend
        auth = backend.CustomLDAPBackend()
        user = auth.authenticate(None, username=self.username, password=self.password)
        self.assertEqual(user.username, 'euclid')

    def test_ldap_view_login(self):
        """ test if authenticates using the auth system login view """
        resp = self.client.post(reverse(ldap_views.ldap_login_view), {
            'username' : self.username,
            'password': self.password
            }, follow=True)
        self.assertEqual(resp.status_code, 200)

    def test_logout(self):
        """ test if logs out using the auth system logout view """
        response = self.client.post(reverse(views.logout), follow=True)
        print(response.content)
        self.assertContains(response, "not logged in")
        self.assertNotContains(response, "euclid")


# Development Login Tests
@unittest.skipIf(devlogin is None, "devlogin not available (not in DEBUG mode)")
@override_settings(DEBUG=True, AUTH_ENABLED_SYSTEMS=['devlogin', 'password'], ALLOWED_HOSTS=['localhost', '127.0.0.1', 'testserver', 'test.example.com', 'example.com'], TEMPLATE_BASE='server_ui/templates/base.html')
class DevLoginTests(TestCase):
    """
    Tests for the development-only authentication system.
    These tests verify that devlogin works correctly and is properly secured.
    """

    def setUp(self):
        """Set up test environment"""
        self.devlogin_url = '/auth/devlogin/login'
        self.auth_start_url = reverse('auth@start', kwargs={'system_name': 'devlogin'})
        self.auth_after_url = reverse('auth@after')

    def test_devlogin_available_in_auth_systems(self):
        """Test that devlogin is available in AUTH_SYSTEMS when DEBUG=True"""
        from django.conf import settings
        if settings.DEBUG:
            self.assertIn('devlogin', AUTH_SYSTEMS)
        else:
            self.assertNotIn('devlogin', AUTH_SYSTEMS)

    def test_localhost_check_function(self):
        """Test the _is_localhost helper function"""
        from django.test import RequestFactory
        from django.conf import settings
        
        factory = RequestFactory()
        
        # Test localhost hosts
        localhost_hosts = ['localhost', '127.0.0.1', 'testserver']
        for host in localhost_hosts:
            request = factory.get('/', HTTP_HOST=host)
            self.assertTrue(devlogin._is_localhost(request), f"Failed for host: {host}")
            
        # Test with port numbers
        request = factory.get('/', HTTP_HOST='localhost:8000')
        self.assertTrue(devlogin._is_localhost(request))
        
        request = factory.get('/', HTTP_HOST='127.0.0.1:8000')
        self.assertTrue(devlogin._is_localhost(request))
        
        # Test test hosts
        request = factory.get('/', HTTP_HOST='test.example.com')
        self.assertTrue(devlogin._is_localhost(request))

    def test_get_auth_url_localhost(self):
        """Test that get_auth_url works for localhost"""
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/', HTTP_HOST='testserver')  # Use testserver for tests
        
        auth_url = devlogin.get_auth_url(request)
        self.assertEqual(auth_url, reverse('auth@devlogin@login'))

    def test_get_auth_url_non_localhost_raises_404(self):
        """Test that get_auth_url raises 404 for non-localhost"""
        from django.test import RequestFactory
        from django.http import Http404
        
        # Use override_settings to disable DEBUG mode for this test
        with self.settings(DEBUG=False):
            factory = RequestFactory()
            request = factory.get('/', HTTP_HOST='example.com')
            
            with self.assertRaises(Http404):
                devlogin.get_auth_url(request)

    def test_get_user_info_after_auth(self):
        """Test that get_user_info_after_auth returns correct user info"""
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/', HTTP_HOST='testserver')  # Use testserver for tests
        
        user_info = devlogin.get_user_info_after_auth(request)
        
        expected_info = {
            'type': 'devlogin',
            'user_id': 'user@example.com',
            'name': 'Development User',
            'info': {
                'email': 'user@example.com',
                'name': 'Development User'
            },
            'token': None
        }
        
        self.assertEqual(user_info, expected_info)

    def test_get_user_info_non_localhost_raises_404(self):
        """Test that get_user_info_after_auth raises 404 for non-localhost"""
        from django.test import RequestFactory
        from django.http import Http404
        
        # Use override_settings to disable DEBUG mode for this test
        with self.settings(DEBUG=False):
            factory = RequestFactory()
            request = factory.get('/', HTTP_HOST='example.com')
            
            with self.assertRaises(Http404):
                devlogin.get_user_info_after_auth(request)

    def test_devlogin_view_get_shows_form(self):
        """Test that GET request to devlogin view shows the login form"""
        response = self.client.get(self.devlogin_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Development Login')
        self.assertContains(response, 'user@example.com')
        self.assertContains(response, 'Development Only')
        self.assertContains(response, 'Login as Development User')

    def test_devlogin_view_post_redirects_to_auth_after(self):
        """Test that POST request to devlogin view redirects to auth/after/"""
        response = self.client.post(self.devlogin_url)
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.auth_after_url)

    def test_full_devlogin_flow(self):
        """Test the complete devlogin authentication flow"""
        # Step 1: Start auth with devlogin
        response = self.client.get(self.auth_start_url)
        self.assertEqual(response.status_code, 302)
        
        # Should redirect to devlogin form
        login_url = response.url
        self.assertTrue(login_url.endswith('/devlogin/login'))
        
        # Step 2: Submit the devlogin form
        response = self.client.post(login_url, follow=True)
        
        # Should end up at the auth/after/ page which processes the login
        self.assertEqual(response.status_code, 200)
        
        # Step 3: Check that user is now logged in
        # The session should contain user info
        session = self.client.session
        self.assertIn('user', session)
        
        user_info = session['user']
        self.assertEqual(user_info['type'], 'devlogin')
        self.assertEqual(user_info['user_id'], 'user@example.com')
        self.assertEqual(user_info['name'], 'Development User')

    def test_devlogin_creates_user_model(self):
        """Test that devlogin creates a User model instance"""
        # Perform login
        self.client.get(self.auth_start_url)
        self.client.post(self.devlogin_url, follow=True)
        
        # Check that user was created in database
        user = models.User.objects.get(user_type='devlogin', user_id='user@example.com')
        self.assertEqual(user.name, 'Development User')
        self.assertEqual(user.info['email'], 'user@example.com')

    def test_devlogin_user_can_logout(self):
        """Test that devlogin user can logout properly"""
        # Login first
        self.client.get(self.auth_start_url)
        self.client.post(self.devlogin_url, follow=True)
        
        # Verify logged in
        session = self.client.session
        self.assertIn('user', session)
        
        # Logout
        response = self.client.post(reverse('auth@logout'), follow=True)
        
        # Verify logged out
        self.assertContains(response, "not logged in")
        session = self.client.session
        self.assertNotIn('user', session)

    def test_auth_system_functions(self):
        """Test other auth system functions work correctly"""
        # Test do_logout (should not raise exception)
        result = devlogin.do_logout({'user_id': 'user@example.com'})
        self.assertIsNone(result)
        
        # Test update_status (should not raise exception)
        devlogin.update_status(None, "test message")
        
        # Test send_message (should not raise exception)
        devlogin.send_message('user@example.com', 'Test User', {}, 'Subject', 'Body')
        
        # Test check_constraint (should always return True)
        result = devlogin.check_constraint({}, {})
        self.assertTrue(result)

    def test_devlogin_login_message_and_icon(self):
        """Test that devlogin has proper login message and icon"""
        self.assertEqual(devlogin.LOGIN_MESSAGE, "Development Login (localhost only)")
        self.assertEqual(devlogin.LOGIN_ICON, "🔧")