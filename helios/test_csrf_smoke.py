"""
Regression tests for the CSRF hardening of state-changing views.

Helios does not use Django's CsrfViewMiddleware; protection is opt-in per view via
check_csrf(). These tests pin down the two properties that makes that safe for the
views that used to be reachable by GET:

  1. the view refuses a GET, a tokenless POST, and a POST with the wrong token; and
  2. the template that drives it renders a POST form carrying the token.
"""

import re
import uuid as uuidlib

from django.test import Client, TestCase

from helios import models
from helios.views import ELGAMAL_PARAMS
from helios_auth.models import User


class CSRFProtectedActionTests(TestCase):
  fixtures = ['users.json']

  def setUp(self):
    self.user = User.objects.get(user_id='ben@adida.net', user_type='google')
    self.user.admin_p = True
    self.user.save()

    self.election, _ = models.Election.get_or_create(
      short_name='csrf-smoke', name='CSRF Smoke', description='d', admin=self.user)
    if not self.election.uuid:
      self.election.uuid = str(uuidlib.uuid4())
      self.election.save()

    self.client = Client()
    self.client.get("/")
    session = self.client.session
    session['user'] = {'type': self.user.user_type, 'user_id': self.user.user_id}
    session.save()

  @property
  def csrf_token(self):
    return self.client.session['csrf_token']

  def election_url(self, path):
    return "/helios/elections/%s%s" % (self.election.uuid, path)

  def assertRejectsUnprotectedRequests(self, url, params):
    """A GET, a tokenless POST, and a POST with a bad token must all be refused."""
    self.assertEqual(self.client.get(url).status_code, 400,
                     "GET should be refused: %s" % url)
    self.assertEqual(self.client.post(url, params).status_code, 400,
                     "POST without a token should be refused: %s" % url)
    self.assertEqual(self.client.post(url, dict(params, csrf_token='wrong')).status_code, 400,
                     "POST with a bad token should be refused: %s" % url)

  def test_election_actions_require_a_csrf_protected_post(self):
    cases = [
      (self.election_url('/archive'), {'archive_p': '1'}),
      (self.election_url('/set_featured'), {'featured_p': '1'}),
      (self.election_url('/set_reg'), {'open_p': '1'}),
      (self.election_url('/copy'), {}),
      (self.election_url('/trustees/add-helios'), {}),
    ]
    for url, params in cases:
      with self.subTest(url=url):
        self.assertRejectsUnprotectedRequests(url, params)
        response = self.client.post(url, dict(params, csrf_token=self.csrf_token))
        self.assertEqual(response.status_code, 302,
                         "a correctly signed POST should be accepted: %s" % url)

  def test_voter_delete_requires_a_csrf_protected_post(self):
    voter = models.Voter.objects.create(
      uuid=str(uuidlib.uuid4()), election=self.election,
      voter_email='voter@test.com', voter_name='Test Voter')
    url = self.election_url('/voters/%s/delete' % voter.uuid)

    self.assertRejectsUnprotectedRequests(url, {})
    self.assertTrue(models.Voter.objects.filter(pk=voter.pk).exists(),
                    "voter must survive every rejected request")

    response = self.client.post(url, {'csrf_token': self.csrf_token})
    self.assertEqual(response.status_code, 302)
    self.assertFalse(models.Voter.objects.filter(pk=voter.pk).exists())

  def test_trustee_actions_require_a_csrf_protected_post(self):
    self.election.generate_trustee(ELGAMAL_PARAMS)
    trustee = self.election.trustee_set.all()[0]

    delete_url = self.election_url('/trustees/delete')
    self.assertRejectsUnprotectedRequests(delete_url, {'uuid': trustee.uuid})
    self.assertRejectsUnprotectedRequests(
      self.election_url('/trustees/%s/sendurl' % trustee.uuid), {})

    response = self.client.post(
      delete_url, {'uuid': trustee.uuid, 'csrf_token': self.csrf_token})
    self.assertEqual(response.status_code, 302)
    self.assertFalse(self.election.trustee_set.filter(pk=trustee.pk).exists())

  def test_voters_upload_cancel_requires_a_csrf_protected_post(self):
    self.assertRejectsUnprotectedRequests(self.election_url('/voters/upload-cancel'), {})

  def test_force_queue_requires_a_csrf_protected_post(self):
    self.assertRejectsUnprotectedRequests("/helios/stats/force-queue", {})

  def assertEveryFormIsProtected(self, html, url):
    forms = re.findall(r'<form\b.*?</form>', html, re.S)
    self.assertTrue(forms, "expected at least one form on %s" % url)
    for form in forms:
      self.assertIn('name="csrf_token"', form,
                    "form without a csrf_token on %s: %s" % (url, form[:200]))

  def test_admin_templates_render_protected_post_forms(self):
    self.election.generate_trustee(ELGAMAL_PARAMS)
    models.Voter.objects.create(
      uuid=str(uuidlib.uuid4()), election=self.election,
      voter_email='voter@test.com', voter_name='Test Voter')

    for path in ['/view', '/trustees/view', '/voters/list']:
      with self.subTest(path=path):
        url = self.election_url(path)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEveryFormIsProtected(response.content.decode(), url)

  def test_action_forms_are_not_nested_in_phrasing_only_elements(self):
    """
    A <form> is flow content, so it may not sit inside a <p> or an <h1>-<h6>. The
    parser also silently closes a <p> at a <form>, which would move these actions
    out of the block they appear to belong to.
    """
    try:
      import html5lib
    except ImportError:
      self.skipTest("html5lib not installed")

    self.election.generate_trustee(ELGAMAL_PARAMS)
    models.Voter.objects.create(
      uuid=str(uuidlib.uuid4()), election=self.election,
      voter_email='voter@test.com', voter_name='Test Voter')

    for path in ['/view', '/trustees/view', '/voters/list']:
      with self.subTest(path=path):
        response = self.client.get(self.election_url(path))
        self.assertEqual(response.status_code, 200)
        document = html5lib.parse(response.content.decode(), treebuilder="etree",
                                  namespaceHTMLElements=False)
        for tag in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
          for element in document.iter(tag):
            self.assertIsNone(
              element.find('.//form'),
              "a <form> is nested inside a <%s> on %s" % (tag, path))

  def test_election_view_renders_the_admin_actions_as_forms(self):
    response = self.client.get(self.election_url('/view'))
    html = response.content.decode()
    for path in ['/archive', '/copy']:
      self.assertIn('action="%s"' % self.election_url(path), html,
                    "%s should be driven by a POST form" % path)
