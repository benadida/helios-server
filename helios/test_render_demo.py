"""Real crypto/task integration; only Google's network exchange is mocked."""
from unittest.mock import Mock, patch
import uuid

from django.test import TestCase, override_settings

from helios import datatypes, models, views
from helios.workflows import homomorphic
from helios_auth.models import User


@override_settings(ALU_STUDENT_DOMAIN='alustudent.com',
                   AUTH_ENABLED_SYSTEMS=['google'],
                   CELERY_TASK_ALWAYS_EAGER=True,
                   CELERY_TASK_EAGER_PROPAGATES=True,
                   CELERY_BROKER_URL='memory://',
                   EMAIL_BACKEND='django.core.mail.backends.dummy.EmailBackend')
class RenderDemoTests(TestCase):
  @override_settings(DEBUG=False)
  def test_demo_assets_load_without_debug_or_collectstatic(self):
    for path in ('/booth/vote.html', '/verifier/verify.html',
                 '/static/helios/main.css', '/static/auth/login-icons/google.png',
                 '/static/main.css'):
      response = self.client.get(path)
      self.assertEqual(response.status_code, 200, path)
      self.assertTrue(b''.join(response.streaming_content), path)

  def google_login(self, email, verified=True):
    session = self.client.session
    session['auth_system_name'] = 'google'
    session['google-oauth-state'] = 'demo-state'
    session['google-redirect-url'] = 'http://localhost:8000/auth/after/'
    session.save()
    response = Mock()
    response.json.return_value = {'email': email, 'email_verified': verified, 'name': 'Demo'}
    with patch('helios_auth.auth_systems.google.get_flow'), \
         patch('helios_auth.auth_systems.google.requests.get', return_value=response):
      return self.client.get('/auth/after/', {'code': 'demo-code', 'state': 'demo-state'})

  def test_wrong_domains_do_not_create_users_or_sessions(self):
    for email in ('staff@alueducation.com', 'person@gmail.com',
                  'student@alustudent.com.attacker.com', 'student@sub.alustudent.com',
                  'student@attacker-alustudent.com'):
      response = self.google_login(email)
      self.assertEqual(response.status_code, 302)
      self.assertNotIn('user', self.client.session)
      self.assertFalse(User.objects.filter(user_id=email).exists())

  def test_unverified_or_nonboolean_verification_rejected(self):
    for verified in (False, 'true', 'false', 1):
      with self.assertRaisesRegex(Exception, 'Email verification failed'):
        self.google_login('student@alustudent.com', verified)
    self.assertEqual(User.objects.count(), 0)

  def test_stale_or_other_auth_users_cannot_register(self):
    admin = User.objects.create(user_type='google', user_id='admin@alustudent.com',
                                info={'email': 'admin@alustudent.com', 'email_verified': True})
    election, _ = models.Election.get_or_create(short_name='eligibility-demo',
                                               uuid=str(uuid.uuid4()),
                                               name='Demo', description='Demo', admin=admin)
    election.openreg = True
    election.save()
    self.assertIn('@alustudent.com', election.pretty_eligibility)
    for auth_type, email, verified in [('google', 'staff@alueducation.com', True),
                                      ('google', 'old@alustudent.com', None),
                                      ('password', 'other@alustudent.com', True)]:
      user = User.objects.create(user_type=auth_type, user_id=email,
                                 info={'email': email, 'email_verified': verified})
      self.assertFalse(election.user_eligible_p(user))
      with self.assertRaises(ValueError):
        models.Voter.register_user_in_election(user, election)
    self.assertEqual(election.voter_set.count(), 0)

  def test_google_auto_registration_cast_verify_close_and_tally(self):
    self.google_login('Organizer@alustudent.com')
    admin = User.objects.get(user_id='organizer@alustudent.com')
    election, _ = models.Election.get_or_create(short_name='render-demo',
                                               uuid=str(uuid.uuid4()),
                                               name='Demo', description='Demo', admin=admin)
    election.questions = [{
      'answer_urls': [None, None], 'answers': ['Alice', 'Bob'],
      'choice_type': 'approval', 'max': 1, 'min': 0, 'question': 'President?',
      'result_type': 'absolute', 'short_name': 'President', 'tally_type': 'homomorphic'
    }]
    election.openreg = True
    election.eligibility = [{'auth_system': 'google'}]
    election.generate_trustee(views.ELGAMAL_PARAMS)
    election.save()
    election.freeze()
    self.assertIn('@alustudent.com', election.pretty_eligibility)
    self.client.get('/auth/logout')
    self.google_login('Voter@alustudent.com')
    voter_user = User.objects.get(user_id='voter@alustudent.com')
    self.assertEqual(election.voter_set.count(), 0)

    vote = homomorphic.EncryptedVote.fromElectionAndAnswers(election, [[1]])
    ballot = vote.ld_object.serialize()
    parsed = datatypes.LDObject.fromDict(vote.ld_object.toJSONDict(),
                                        type_hint='legacy/EncryptedVote')
    self.assertTrue(parsed.wrapped_obj.verify(election))
    base = f'/helios/elections/{election.uuid}'
    self.assertEqual(self.client.post(base + '/cast', {'encrypted_vote': ballot}).status_code, 302)
    self.assertEqual(self.client.get(base + '/cast_confirm').status_code, 200)
    self.assertEqual(election.voter_set.count(), 1)
    # Repeated confirmation must not create duplicate voter records.
    self.client.get(base + '/cast_confirm')
    self.assertEqual(election.voter_set.count(), 1)
    token = self.client.session['csrf_token']
    self.assertEqual(self.client.post(base + '/cast_confirm', {'csrf_token': token}).status_code, 302)
    voter = models.Voter.get_by_election_and_user(election, voter_user)
    cast = models.CastVote.objects.get(voter=voter)
    self.assertIsNotNone(cast.verified_at)
    self.assertIsNone(cast.invalidated_at)
    voter.refresh_from_db()
    self.assertEqual(voter.vote_hash, cast.vote_hash)
    tracker_page = self.client.get(views.get_castvote_url(cast))
    self.assertContains(tracker_page, cast.vote_hash)

    session = self.client.session
    session['user'] = {'type': 'google', 'user_id': admin.user_id}
    session.save()
    token = self.client.session['csrf_token']
    self.assertEqual(self.client.post(base + '/compute_tally', {'csrf_token': token}).status_code, 302)
    election.refresh_from_db()
    self.assertTrue(election.voting_has_stopped())
    self.assertIsNotNone(election.encrypted_tally)
    self.assertIsNotNone(election.get_helios_trustee().decryption_proofs)
    self.assertEqual(self.client.post(base + '/combine_decryptions', {'csrf_token': token}).status_code, 302)
    self.assertEqual(self.client.get(base + '/result').status_code, 403)
    self.assertEqual(self.client.post(base + '/release_result', {'csrf_token': token}).status_code, 302)
    self.assertEqual(self.client.get(base + '/result').json(), [[0, 1]])
    session = self.client.session
    session['user'] = {'type': 'google', 'user_id': voter_user.user_id}
    session.save()
    self.client.post(base + '/cast', {'encrypted_vote': ballot})
    self.client.post(base + '/cast_confirm', {'csrf_token': token})
    self.assertEqual(models.CastVote.objects.filter(voter=voter).count(), 1)
