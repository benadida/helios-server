"""
Unit Tests for Auth Systems
"""

import json
import unittest

from django.core import mail
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from . import models, views
from .auth_systems import AUTH_SYSTEMS, password as password_views
from .utils import format_recipient


class FormatRecipientTests(unittest.TestCase):
    """Tests for the format_recipient helper function"""

    def test_basic_formatting(self):
        """Test basic name and email formatting"""
        result = format_recipient("John Doe", "john@example.com")
        self.assertEqual(result, "\"John Doe\" <john@example.com>")

    def test_truncates_long_name(self):
        """Test that names longer than 70 characters are truncated"""
        long_name = "A" * 100
        result = format_recipient(long_name, "test@example.com")
        self.assertEqual(result, "\"%s\" <test@example.com>" % ("A" * 70))

    def test_empty_name_uses_email(self):
        """Test that empty name falls back to email"""
        result = format_recipient("", "test@example.com")
        self.assertEqual(result, "\"test@example.com\" <test@example.com>")

    def test_none_name_uses_email(self):
        """Test that None name falls back to email"""
        result = format_recipient(None, "test@example.com")
        self.assertEqual(result, "\"test@example.com\" <test@example.com>")

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


class GitHubUserTests(TestCase):
    """
    Tests specific to GitHub authentication, particularly case-insensitive username matching.
    GitHub usernames are case-insensitive, so 'JohnDoe', 'johndoe', and 'JOHNDOE' should all
    refer to the same user.
    """

    def test_github_case_insensitive_update_or_create(self):
        """
        Test that update_or_create matches GitHub users case-insensitively
        """
        # Create a user with mixed case
        u1 = models.User.update_or_create(
            user_type='github',
            user_id='JohnDoe',
            name='John Doe (JohnDoe)',
            info={'email': 'john@example.com'}
        )

        # Login again with lowercase - should return the same user
        u2 = models.User.update_or_create(
            user_type='github',
            user_id='johndoe',
            name='John Doe (johndoe)',
            info={'email': 'john@example.com'}
        )

        # Should be the same database record
        self.assertEqual(u1.id, u2.id)

        # The user_id should be updated to the new case
        u2.refresh_from_db()
        self.assertEqual(u2.user_id, 'johndoe')

    def test_github_case_insensitive_get_by_type_and_id(self):
        """
        Test that get_by_type_and_id finds GitHub users case-insensitively
        """
        # Create a user with uppercase
        models.User.update_or_create(
            user_type='github',
            user_id='TESTUSER',
            name='Test User (TESTUSER)',
            info={'email': 'test@example.com'}
        )

        # Should find the user with lowercase
        u = models.User.get_by_type_and_id('github', 'testuser')
        self.assertEqual(u.user_id, 'TESTUSER')

        # Should find the user with mixed case
        u = models.User.get_by_type_and_id('github', 'TestUser')
        self.assertEqual(u.user_id, 'TESTUSER')

    def test_github_preserves_display_case(self):
        """
        Test that the username case is preserved from the most recent login
        """
        # First login with lowercase
        u1 = models.User.update_or_create(
            user_type='github',
            user_id='myuser',
            name='My User (myuser)',
            info={'email': 'my@example.com'}
        )
        self.assertEqual(u1.user_id, 'myuser')

        # Second login with mixed case - should update stored case
        u2 = models.User.update_or_create(
            user_type='github',
            user_id='MyUser',
            name='My User (MyUser)',
            info={'email': 'my@example.com'}
        )
        self.assertEqual(u2.user_id, 'MyUser')

        # Verify it's the same user
        self.assertEqual(u1.id, u2.id)

    def test_password_auth_still_case_sensitive(self):
        """
        Test that password auth remains case-sensitive (not affected by GitHub changes)
        """
        # Create a user with mixed case
        u1 = models.User.update_or_create(
            user_type='password',
            user_id='TestUser@example.com',
            name='Test User',
            info={'password': 'hashed_password'}
        )

        # Create another user with different case - should be a new user
        u2 = models.User.update_or_create(
            user_type='password',
            user_id='testuser@example.com',
            name='Test User 2',
            info={'password': 'hashed_password2'}
        )

        # Should be different users
        self.assertNotEqual(u1.id, u2.id)


# FIXME: login CSRF should make these tests more complicated
# and should be tested for

class AuthCallbackFailureTests(TestCase):
    """
    A login callback that can't be completed (replayed with the back button or a
    refresh, so the OAuth state is gone, or a code the provider rejects) should
    show a "try again" page, not a 500.
    """

    def _start_session(self, system_name, return_url):
        self.client.get("/")
        session = self.client.session
        session['auth_system_name'] = system_name
        session['auth_return_url'] = return_url
        session.save()

    def test_replayed_callback_shows_try_again_page(self):
        for system_name in ['google', 'github']:
            self._start_session(system_name, '/helios/e/test-election')

            # no OAuth state left in the session, as after a first callback already used it
            response = self.client.get(reverse('auth@after'), {'code': 'used_code', 'state': 'used_state'})

            self.assertEqual(response.status_code, 400)
            self.assertContains(response, "Try signing in again", status_code=400)
            self.assertContains(response, reverse('auth@start', kwargs={'system_name': system_name}), status_code=400)
            self.assertContains(response, "return_url=/helios/e/test-election", status_code=400)
            self.assertNotIn('user', self.client.session)

    def test_replayed_callback_after_completed_sign_in_keeps_return_url(self):
        from unittest import mock
        from .auth_systems import google

        self._start_session('google', '/helios/e/test-election')

        # first callback succeeds and sends the person back to the election
        user_info = {'type': 'google', 'user_id': 'voter@example.com', 'name': 'Voter',
                     'info': {'email': 'voter@example.com'}, 'token': {}}
        with mock.patch.object(google, 'get_user_info_after_auth', return_value=user_info):
            response = self.client.get(reverse('auth@after'), {'code': 'code', 'state': 'state'}, follow=True)
        self.assertEqual(self.client.session['user']['user_id'], 'voter@example.com')

        # the back button replays the same callback, whose OAuth state is now used up
        response = self.client.get(reverse('auth@after'), {'code': 'code', 'state': 'state'})

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "return_url=/helios/e/test-election", status_code=400)

    def _github_callback(self, user_response, emails_response):
        from unittest import mock
        from .auth_systems import github

        self._start_session('github', '/helios/e/test-election')
        session = self.client.session
        session['gh_oauth_state'] = 'the_state'
        session['gh_redirect_uri'] = 'http://testserver/auth/after/'
        session.save()

        oauth = mock.MagicMock()
        oauth.get.side_effect = lambda url: emails_response if url.endswith('/emails') else user_response
        with mock.patch.object(github, 'get_oauth_session', return_value=oauth):
            return self.client.get(reverse('auth@after'), {'code': 'the_code', 'state': 'the_state'})

    def _json_response(self, data, status_code=200):
        import requests
        response = requests.Response()
        response.status_code = status_code
        response._content = json.dumps(data).encode()
        return response

    def test_github_unverified_primary_email_explains_how_to_fix(self):
        response = self._github_callback(
            self._json_response({'login': 'octocat', 'name': 'Octo Cat'}),
            self._json_response([
                {'email': 'octo@example.com', 'primary': True, 'verified': False},
                {'email': 'other@example.com', 'primary': False, 'verified': True},
            ]))

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "doesn&#x27;t have a verified primary email address", status_code=400)
        self.assertContains(response, 'href="https://github.com/settings/emails"', status_code=400)
        self.assertContains(response, "Try signing in again", status_code=400)
        self.assertContains(response, "return_url=/helios/e/test-election", status_code=400)
        self.assertNotIn('user', self.client.session)
        self.assertFalse(models.User.objects.filter(user_type='github', user_id__iexact='octocat').exists())

    def test_github_api_failure_says_to_retry_later(self):
        response = self._github_callback(
            self._json_response({'message': 'Server Error'}, status_code=502),
            self._json_response([]))

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "GitHub didn&#x27;t send back your account details", status_code=400)
        self.assertNotIn('user', self.client.session)

    def test_github_verified_primary_email_signs_in(self):
        response = self._github_callback(
            self._json_response({'login': 'octocat', 'name': 'Octo Cat'}),
            self._json_response([{'email': 'octo@example.com', 'primary': True, 'verified': True}]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session['user']['user_id'], 'octocat')


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

    def test_ldap_email_is_plain_text_only(self):
        ldap_views.send_message('jdoe', 'J Doe', {'email': 'jdoe@example.com'}, "subject", "Use <VOTER_ID>\nthen vote")

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].alternatives, [])
        self.assertEqual(mail.outbox[0].body, "Use <VOTER_ID>\nthen vote")

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
        if user is None:
            self.skipTest("LDAP server unavailable - skipping test")
        self.assertEqual(user.username, 'euclid')

    def test_ldap_view_login(self):
        """ test if authenticates using the auth system login view """
        # prime the session so that it carries a csrf_token, the way rendering the
        # login form would
        self.client.get(reverse(ldap_views.ldap_login_view))

        resp = self.client.post(reverse(ldap_views.ldap_login_view), {
            'username' : self.username,
            'password': self.password,
            'csrf_token': self.client.session['csrf_token']
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
@override_settings(DEBUG=True, AUTH_ENABLED_SYSTEMS=['devlogin', 'password'], ALLOWED_HOSTS=['localhost', '127.0.0.1', 'testserver'], TEMPLATE_BASE='server_ui/templates/base.html')
class DevLoginTests(TestCase):
    """Tests for the development-only authentication system."""

    def test_full_devlogin_flow(self):
        """Test the complete devlogin authentication flow"""
        # Start auth, submit form, verify logged in
        response = self.client.get(reverse('auth@start', kwargs={'system_name': 'devlogin'}))
        response = self.client.post(response.url, follow=True)

        self.assertIn('user', self.client.session)
        self.assertEqual(self.client.session['user']['type'], 'devlogin')
        self.assertEqual(self.client.session['user']['user_id'], 'user@example.com')

    def test_devlogin_blocked_when_not_localhost(self):
        """Test that devlogin is blocked for non-localhost requests"""
        from django.test import RequestFactory
        from django.http import Http404

        with self.settings(DEBUG=False):
            factory = RequestFactory()
            request = factory.get('/', HTTP_HOST='example.com')

            with self.assertRaises(Http404):
                devlogin.get_auth_url(request)


class OAuthAuthSystemTests(TestCase):
    """
    Tests for OAuth-based authentication systems (Google, GitHub, GitLab, LinkedIn)
    """

    def test_oauth_systems_have_required_interface(self):
        """Verify OAuth auth systems implement required interface methods"""
        oauth_systems = ['google', 'github', 'gitlab', 'linkedin']
        required_methods = [
            'get_auth_url',
            'get_user_info_after_auth',
            'do_logout',
            'send_message',
            'can_create_election',
        ]

        for system_name in oauth_systems:
            if system_name not in AUTH_SYSTEMS:
                continue
            system = AUTH_SYSTEMS[system_name]
            for method in required_methods:
                self.assertTrue(
                    hasattr(system, method),
                    f"{system_name} missing required method: {method}"
                )

    def test_oauth_state_verification_rejects_missing_state(self):
        """Verify OAuth state verification rejects requests with missing state"""
        from django.test import RequestFactory
        from .auth_systems import google, github, gitlab, linkedin

        factory = RequestFactory()

        for system, session_key in [
            (google, 'google-oauth-state'),
            (github, 'gh_oauth_state'),
            (gitlab, 'gl_oauth_state'),
            (linkedin, 'linkedin_oauth_state'),
        ]:
            # Create request with code but no state
            request = factory.get('/auth/after/', {'code': 'test_code'})
            request.session = {}

            with self.assertRaises(Exception) as context:
                system.get_user_info_after_auth(request)
            self.assertIn('state mismatch', str(context.exception).lower())

    def test_oauth_state_verification_rejects_wrong_state(self):
        """Verify OAuth state verification rejects requests with wrong state"""
        from django.test import RequestFactory
        from .auth_systems import google, github, gitlab, linkedin

        factory = RequestFactory()

        test_cases = [
            (google, 'google-oauth-state', 'google-redirect-url'),
            (github, 'gh_oauth_state', 'gh_redirect_uri'),
            (gitlab, 'gl_oauth_state', 'gl_redirect_uri'),
            (linkedin, 'linkedin_oauth_state', 'linkedin_redirect_uri'),
        ]

        for system, state_key, redirect_key in test_cases:
            # Create request with code and wrong state
            request = factory.get('/auth/after/', {
                'code': 'test_code',
                'state': 'wrong_state'
            })
            request.session = {
                state_key: 'correct_state',
                redirect_key: 'http://example.com/callback'
            }

            with self.assertRaises(Exception) as context:
                system.get_user_info_after_auth(request)
            self.assertIn('state mismatch', str(context.exception).lower())

    def test_oauth_returns_none_without_code(self):
        """Verify OAuth auth returns None when no code is provided"""
        from django.test import RequestFactory
        from .auth_systems import google, github, gitlab, linkedin

        factory = RequestFactory()
        request = factory.get('/auth/after/')
        request.session = {}

        for system in [google, github, gitlab, linkedin]:
            result = system.get_user_info_after_auth(request)
            self.assertIsNone(result)
