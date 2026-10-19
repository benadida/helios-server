"""Bridge browser security and real Helios crypto integration."""
import datetime
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
import uuid
from urllib.parse import parse_qs, urlsplit
from unittest.mock import Mock, patch

from django.test import Client, TestCase, override_settings
from django.core.management import call_command, CommandError
from io import StringIO
from types import SimpleNamespace
from django.urls import reverse
from helios import datatypes, models, views
from helios.workflows import homomorphic
from helios_auth.bridge_protocol import challenge
from helios_auth.models import BridgeLoginRequest, User
from helios.security import get_voter


@override_settings(AUTH_ENABLED_SYSTEMS=['alu'], ALU_STUDENT_DOMAIN='alustudent.com',
  ALU_BRIDGE_APP_ORIGIN='https://alu.example', SECURE_URL_HOST='https://helios.example',
  ALU_BRIDGE_SECRET='test-only-secret-with-at-least-32-bytes',
  ALU_BRIDGE_CLIENT_ID='alu-helios-demo', CELERY_TASK_ALWAYS_EAGER=True,
  CELERY_TASK_EAGER_PROPAGATES=True, CELERY_BROKER_URL='memory://',
  EMAIL_BACKEND='django.core.mail.backends.dummy.EmailBackend')
class BridgeTests(TestCase):
  def setUp(self):
    # Isolate process-cache rate counters between independent test identities.
    from django.core.cache import cache
    cache.clear()
    self.admin = User.objects.create(user_type='alu', user_id='organizer', admin_p=True,
      info={'email': 'organizer@alustudent.com', 'email_verified': True})
    self.election, _ = models.Election.get_or_create(short_name='bridge-test',
      uuid=str(uuid.uuid4()), name='TEST Bridge', description='TEST', admin=self.admin)
    self.election.openreg = True
    self.election.eligibility = [{'auth_system': 'alu'}]
    self.election.save()
    self.override = override_settings(ALU_BRIDGE_ELECTIONS=(self.election.uuid,))
    self.override.enable()
    self.addCleanup(self.override.disable)
    self.committee_subjects = set()
    self.policy_events = {}
    self.cross_language_status = False
    def fresh_status(url, **kwargs):
      payload = kwargs['json']
      if self.cross_language_status:
        data = self.fixture_call({'action': 'eligibility',
          'authorization': kwargs['headers']['Authorization'], 'grant': payload})
        result = Mock(status_code=data['status'])
        result.json.return_value = data['data']
        return result
      result = Mock(status_code=200)
      result.json.return_value = {'binding': {'client_id': payload['client_id'],
        'election_id': payload['election_id']}, 'voters': [
        {'subject': v['subject'], 'student': True,
         'committee': v['subject'] in self.committee_subjects,
         'events': self.policy_events.get(v['subject'], []) if v['cast_at'] else []}
        for v in payload['voters']]}
      return result
    self.status_patch = patch('helios.bridge_eligibility.requests.post', side_effect=fresh_status)
    self.status_patch.start()
    self.addCleanup(self.status_patch.stop)

  def begin(self, client=None):
    client = client or self.client
    result = client.get('/auth/alu/start/' + self.election.uuid + '/')
    self.assertEqual(result.status_code, 302)
    self.assertTrue(result.url.startswith('https://alu.example/helios/authorize#request='))
    self.assertEqual(result['Referrer-Policy'], 'no-referrer')
    return client.session['alu_pending']

  def finish(self, pending, subject='student', email='student@alustudent.com', verified=True,
             client=None, binding=None, expiry=None, code=None, access_kind='voter'):
    client = client or self.client
    result = Mock(status_code=200)
    result.json.return_value = {'identity': {'subject': subject, 'email': email,
      'email_verified': verified, 'name': 'Student'}, 'binding': binding or {
      'client_id': 'alu-helios-demo', 'election_id': self.election.uuid,
      'state': pending['state'], 'code_challenge': challenge(pending['verifier'])},
      'session_expires_at': expiry or time.time() + 290, 'access_kind': access_kind}
    with patch('helios_auth.bridge_views.requests.post', return_value=result) as post:
      response = client.post('/auth/alu/complete/', {'code': code or secrets.token_urlsafe(32),
        'state': pending['state'], 'csrf_token': client.session['csrf_token']},
        HTTP_ORIGIN='https://helios.example')
    return response, post

  def test_student_login_rotates_session_and_cannot_administer(self):
    pending = self.begin()
    old_key = self.client.session.session_key
    result, post = self.finish(pending)
    self.assertEqual(result.status_code, 200)
    self.assertNotEqual(old_key, self.client.session.session_key)
    user = User.objects.get(user_id='student')
    self.assertFalse(user.admin_p)
    self.assertFalse(user.can_create_election())
    self.assertFalse(views.user_can_admin_election(user, self.election))
    self.assertEqual(post.call_args.kwargs['headers']['Authorization'], 'Bearer test-only-secret-with-at-least-32-bytes')
    self.assertFalse(post.call_args.kwargs['allow_redirects'])
    result, post = self.finish(pending)
    self.assertEqual(result.status_code, 403)
    post.assert_not_called()

  def test_existing_authorized_admin_preserved(self):
    result, _ = self.finish(self.begin(), subject='organizer', email='organizer@alustudent.com', access_kind='committee')
    self.assertEqual(result.status_code, 200)
    self.admin.refresh_from_db()
    self.assertTrue(self.admin.admin_p)
    self.assertTrue(views.user_can_admin_election(self.admin, self.election))
    self.assertEqual(self.client.get(f'/helios/elections/{self.election.uuid}/voters/upload').status_code, 403)
    self.assertEqual(self.client.get(f'/helios/elections/{self.election.uuid}/view').status_code, 200)
    self.assertEqual(self.client.post(f'/helios/elections/{self.election.uuid}/cast',
      {'encrypted_vote': 'ignored'}).status_code, 403)

  def test_committee_code_cannot_enroll_or_grant_admin(self):
    result, _ = self.finish(self.begin(), access_kind='committee')
    self.assertEqual(result.status_code, 403)
    self.assertFalse(User.objects.filter(user_id='student').exists())
    self.assertEqual(self.election.voter_set.count(), 0)

  def test_role_change_blocks_existing_session_direct_urls_and_registration(self):
    self.finish(self.begin())
    self.committee_subjects.add('student')
    base = f'/helios/elections/{self.election.uuid}'
    for path, body in [('/cast', {'encrypted_vote': 'ignored'}),
                       ('/register', {'csrf_token': self.client.session['csrf_token']}),
                       ('/cast_confirm', {'csrf_token': self.client.session['csrf_token']})]:
      self.assertEqual(self.client.post(base + path, body).status_code, 403)
    self.assertEqual(self.client.get(base + '/cast_confirm').status_code, 403)
    self.assertEqual(self.election.voter_set.count(), 0)
    self.assertEqual(models.CastVote.objects.count(), 0)
    self.assertIn('user', self.client.session)

  def test_fresh_membership_failure_and_forged_reply_fail_closed(self):
    self.finish(self.begin())
    base = f'/helios/elections/{self.election.uuid}'
    for response in [Mock(status_code=503), Mock(status_code=200)]:
      response.json.return_value = {'binding': {}, 'voters': []}
      with patch('helios.bridge_eligibility.requests.post', return_value=response):
        self.assertEqual(self.client.post(base + '/cast', {'encrypted_vote': 'ignored'}).status_code, 403)

  def prepare_encrypted_ballot(self):
    election = self.election
    election.questions = [{'answer_urls':[None,None], 'answers':['Alice','Bob'],
      'choice_type':'approval', 'max':1, 'min':0, 'question':'President?',
      'result_type':'absolute', 'short_name':'President', 'tally_type':'homomorphic'}]
    election.generate_trustee(views.ELGAMAL_PARAMS)
    election.save()
    election.freeze()
    self.finish(self.begin())
    vote = homomorphic.EncryptedVote.fromElectionAndAnswers(election, [[1]])
    base = f'/helios/elections/{election.uuid}'
    self.assertEqual(self.client.post(base+'/cast', {'encrypted_vote':vote.ld_object.serialize()}).status_code, 302)
    self.assertEqual(self.client.get(base+'/cast_confirm').status_code, 200)
    return base

  def test_committee_change_between_confirmation_and_acceptance_blocks_ballot(self):
    base = self.prepare_encrypted_ballot()
    self.committee_subjects.add('student')
    self.assertEqual(self.client.post(base+'/cast_confirm',
      {'csrf_token':self.client.session['csrf_token']}).status_code, 403)
    self.assertEqual(models.CastVote.objects.count(), 0)
    self.assertIsNone(self.election.voter_set.get().vote)

  def test_membership_after_ballot_is_flagged_preserved_and_requires_policy(self):
    base = self.prepare_encrypted_ballot()
    self.assertEqual(self.client.post(base+'/cast_confirm',
      {'csrf_token':self.client.session['csrf_token']}).status_code, 302)
    cast = models.CastVote.objects.get()
    original_vote = cast.vote.ld_object.serialize()
    self.committee_subjects.add('student')
    self.policy_events['student'] = ['123']
    self.assertEqual(self.client.post(base+'/cast', {'encrypted_vote':'ignored'}).status_code, 403)
    review = models.BallotPolicyReview.objects.get()
    self.assertEqual(review.decision, 'pending')
    cast.refresh_from_db()
    self.assertIsNotNone(cast.verified_at)
    self.assertIsNone(cast.invalidated_at)
    self.assertEqual(cast.vote.ld_object.serialize(), original_vote)
    self.assertEqual(self.client.post(base+'/policy_reviews', {'decision':'retain',
      'review_id':review.id, 'reason':'Student cannot decide this',
      'csrf_token':self.client.session['csrf_token']}).status_code, 403)
    self.client = Client()
    self.finish(self.begin(), subject='organizer', email='organizer@alustudent.com', access_kind='committee')
    token = self.client.session['csrf_token']
    self.assertContains(self.client.get(base+'/policy_reviews'), 'Pending reviews block tallying')
    self.assertEqual(self.client.post(base+'/compute_tally', {'csrf_token':token}).status_code, 403)
    from django.core.exceptions import PermissionDenied
    with self.assertRaises(PermissionDenied):
      self.election.compute_tally()
    self.assertEqual(self.client.post(base+'/policy_reviews', {'decision':'delete',
      'review_id':review.id, 'reason':'Never silently delete', 'csrf_token':token}).status_code, 400)
    self.assertEqual(self.client.post(base+'/policy_reviews', {'decision':'retain',
      'review_id':review.id, 'reason':'Policy retains votes cast before appointment', 'csrf_token':token}).status_code, 302)
    review.refresh_from_db()
    self.assertEqual(review.decided_by, self.admin)
    self.assertEqual(review.decision, 'retain')
    # Revocation cannot erase the historical transition or its decision.
    self.committee_subjects.clear()
    self.assertEqual(self.client.post(base+'/compute_tally', {'csrf_token':token}).status_code, 302)
    self.assertEqual(models.CastVote.objects.count(), 1)
    # A later, distinct appointment requires another explicit decision.
    self.policy_events['student'].append('124')
    self.client.get(base+'/policy_reviews')
    self.assertEqual(models.BallotPolicyReview.objects.filter(decision='pending').count(), 1)

  def test_operator_bootstrap_grants_only_one_election(self):
    election_id, subject = str(uuid.uuid4()), str(uuid.uuid4())
    with override_settings(ALU_BRIDGE_ELECTIONS=(election_id,)):
      call_command('setup_alu_demo', election_id=election_id, admin_subject=subject,
        admin_email='organizer@alustudent.com', stdout=StringIO())
      organizer = User.objects.get(user_type='alu', user_id=subject)
      self.assertFalse(organizer.admin_p)
      self.assertFalse(organizer.can_create_election())
      created = models.Election.get_by_uuid(election_id)
      self.assertTrue(views.user_can_admin_election(organizer, created))
      self.assertIsNone(created.frozen_at)
      with self.assertRaises(CommandError):
        call_command('setup_alu_demo', election_id=election_id, admin_subject=str(uuid.uuid4()),
          admin_email='other@alustudent.com', stdout=StringIO())
      self.assertEqual(created.admin, organizer)

  def test_state_origin_csrf_and_different_browser_rejected(self):
    pending = self.begin()
    with patch('helios_auth.bridge_views.requests.post') as post:
      for state, origin, csrf in [('tampered', 'https://helios.example', self.client.session['csrf_token']),
        (pending['state'], 'https://attacker.example', self.client.session['csrf_token']),
        (pending['state'], 'https://helios.example', 'wrong')]:
        result = self.client.post('/auth/alu/complete/', {'code': secrets.token_urlsafe(32),
          'state': state, 'csrf_token': csrf}, HTTP_ORIGIN=origin)
        self.assertIn(result.status_code, (400, 403))
      other = Client()
      other.get('/auth/alu/callback/')
      result = other.post('/auth/alu/complete/', {'code': secrets.token_urlsafe(32),
        'state': pending['state'], 'csrf_token': other.session['csrf_token']}, HTTP_ORIGIN='https://helios.example')
      self.assertEqual(result.status_code, 403)
      post.assert_not_called()

  def test_expired_browser_request_rejected_before_exchange(self):
    pending = self.begin()
    BridgeLoginRequest.objects.update(expires_at=datetime.datetime.utcnow()-datetime.timedelta(seconds=1))
    result, post = self.finish(pending)
    self.assertEqual(result.status_code, 403)
    post.assert_not_called()

  def test_forged_identity_wrong_binding_and_expiry_rejected(self):
    for kw in [{'email':'student@alustudent.com.evil'}, {'verified':False}, {'verified':'true'},
      {'binding':{'election_id':str(uuid.uuid4())}}, {'expiry':time.time()-1}, {'expiry':float('inf')}]:
      self.client = Client()
      result, _ = self.finish(self.begin(), **kw)
      self.assertEqual(result.status_code, 403)
      self.assertFalse(User.objects.filter(user_id='student').exists())

  def test_registration_closed_and_private_election_rejected(self):
    for field in ('openreg', 'private_p'):
      self.election.openreg = field != 'openreg'
      self.election.private_p = field == 'private_p'
      self.election.save()
      self.client = Client()
      result, _ = self.finish(self.begin())
      self.assertEqual(result.status_code, 403)
      self.assertFalse(User.objects.filter(user_id='student').exists())

  def test_wrong_election_access_and_expired_session_rejected(self):
    self.finish(self.begin())
    other, _ = models.Election.get_or_create(short_name='other', uuid=str(uuid.uuid4()),
      name='Other', description='TEST', admin=self.admin)
    self.assertEqual(self.client.get(f'/helios/elections/{other.uuid}/view').status_code, 403)
    session = self.client.session
    session['alu_session_expires_at'] = time.time()-1
    session['CURRENT_VOTER_ID'] = 99999
    session.save()
    self.client.get('/auth/alu/callback/')
    self.assertNotIn('user', self.client.session)
    self.assertNotIn('CURRENT_VOTER_ID', self.client.session)

  def test_legacy_voter_session_cannot_bypass_bridge_or_substitute_account(self):
    legacy = models.Voter.objects.create(uuid=str(uuid.uuid4()), election=self.election,
      voter_login_id='legacy', voter_password='test-only', voter_email='outsider@example.com')
    session = self.client.session
    session['CURRENT_VOTER_ID'] = legacy.id
    session.save()
    self.assertIsNone(get_voter(SimpleNamespace(session=session), None, self.election))
    self.assertEqual(self.client.get(reverse(views.password_voter_login,
      args=[self.election.uuid])).status_code, 403)
    self.finish(self.begin())
    user = User.objects.get(user_id='student')
    own = models.Voter.register_user_in_election(user, self.election)
    session = self.client.session
    session['CURRENT_VOTER_ID'] = legacy.id
    self.assertEqual(get_voter(SimpleNamespace(session=session), user, self.election), own)

  def test_auto_registration_encrypted_ballot_verification_and_eager_tally(self):
    if os.environ.get('BRIDGE_TEST_DATABASE_URL'):
      self.finish = self.cross_language_finish
      self.cross_language_status = True
    election = self.election
    election.questions = [{'answer_urls':[None,None], 'answers':['Alice','Bob'],
      'choice_type':'approval', 'max':1, 'min':0, 'question':'President?',
      'result_type':'absolute', 'short_name':'President', 'tally_type':'homomorphic'}]
    election.generate_trustee(views.ELGAMAL_PARAMS)
    election.save()
    election.freeze()
    self.assertEqual(self.finish(self.begin())[0].status_code, 200)
    student = User.objects.get(user_id='student')
    self.assertEqual(election.voter_set.count(), 0)
    vote = homomorphic.EncryptedVote.fromElectionAndAnswers(election, [[1]])
    parsed = datatypes.LDObject.fromDict(vote.ld_object.toJSONDict(), type_hint='legacy/EncryptedVote')
    self.assertTrue(parsed.wrapped_obj.verify(election))
    base = f'/helios/elections/{election.uuid}'
    self.assertEqual(self.client.post(base+'/cast', {'encrypted_vote':vote.ld_object.serialize()}).status_code, 302)
    self.assertEqual(self.client.get(base+'/cast_confirm').status_code, 200)
    self.client.get(base+'/cast_confirm')
    self.assertEqual(election.voter_set.count(), 1)
    token = self.client.session['csrf_token']
    self.assertEqual(self.client.post(base+'/cast_confirm', {'csrf_token':token}).status_code, 302)
    voter = models.Voter.get_by_election_and_user(election, student)
    cast = models.CastVote.objects.get(voter=voter)
    self.assertIsNotNone(cast.verified_at)
    self.assertContains(self.client.get(views.get_castvote_url(cast)), cast.vote_hash)
    # Student cannot invoke committee operations; explicit election admin can.
    self.assertEqual(self.client.post(base+'/compute_tally', {'csrf_token':token}).status_code, 403)
    self.client = Client()
    self.assertEqual(self.finish(self.begin(), subject='organizer', email='organizer@alustudent.com')[0].status_code, 200)
    token = self.client.session['csrf_token']
    self.assertEqual(self.client.post(base+'/compute_tally', {'csrf_token':token}).status_code, 302)
    election.refresh_from_db()
    self.assertTrue(election.voting_has_stopped())
    self.assertIsNotNone(election.get_helios_trustee().decryption_proofs)
    self.assertEqual(self.client.post(base+'/combine_decryptions', {'csrf_token':token}).status_code, 302)
    self.assertEqual(self.client.post(base+'/release_result', {'csrf_token':token}).status_code, 302)
    self.assertEqual(self.client.get(base+'/result').json(), [[0,1]])

  def cross_language_finish(self, pending, subject='student', email='student@alustudent.com'):
    from django.conf import settings
    from helios_auth.bridge_protocol import sign_request
    call = self.fixture_call
    signed = sign_request({'v': 1, 'client_id': settings.ALU_BRIDGE_CLIENT_ID,
      'election_id': self.election.uuid, 'state': pending['state'],
      'code_challenge': challenge(pending['verifier']),
      'redirect_uri': settings.SECURE_URL_HOST + '/auth/alu/callback/', 'exp': pending['expires']})
    result = call({'action': 'authorize', 'request': signed, 'subject': subject, 'email': email})
    self.assertEqual(result['status'], 200)
    code = parse_qs(urlsplit(result['data']['callback']).fragment)['code'][0]
    def exchange(url, **kwargs):
      data = call({'action': 'exchange', 'authorization': kwargs['headers']['Authorization'],
                   'grant': kwargs['json']})
      response = Mock(status_code=data['status'])
      response.json.return_value = data['data']
      return response
    with patch('helios_auth.bridge_views.requests.post', side_effect=exchange) as post:
      response = self.client.post('/auth/alu/complete/', {'code': code, 'state': pending['state'],
        'csrf_token': self.client.session['csrf_token']}, HTTP_ORIGIN=settings.SECURE_URL_HOST)
    self.assertEqual(response.status_code, 200)
    replay = call({'action': 'exchange', 'authorization': 'Bearer ' + settings.ALU_BRIDGE_SECRET,
                  'grant': post.call_args.kwargs['json']})
    self.assertEqual(replay['status'], 400)
    return response, post

  def fixture_call(self, data):
    from django.conf import settings
    data['config'] = {'secret': settings.ALU_BRIDGE_SECRET, 'clientId': settings.ALU_BRIDGE_CLIENT_ID,
      'appOrigin': settings.ALU_BRIDGE_APP_ORIGIN, 'heliosOrigin': settings.SECURE_URL_HOST,
      'elections': [self.election.uuid]}
    fixture = Path(__file__).resolve().parents[2] / 'ALU_Election_App/scripts/helios-bridge-fixture.mjs'
    result = subprocess.run(['node', str(fixture)], input=json.dumps(data),
      text=True, capture_output=True, check=True, timeout=15)
    return json.loads(result.stdout)
