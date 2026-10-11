"""Actual ALU React booth -> unmodified JS crypto -> Helios cast and tally."""
import json
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, local
from django.db import close_old_connections, connections
from django.test import TransactionTestCase, override_settings
from pathlib import Path
from unittest.mock import Mock, patch

from django.conf import settings
from django.test import Client
from helios import datatypes, models, views
from helios.workflows import homomorphic
from helios_auth import test_bridge


class AluUiTests(test_bridge.BridgeTests):
  # Reuse the isolated, validated session fixture and membership checks, never
  # manufacture a Neon identity or grant in the production database.
  def frozen_ballot(self):
    self.election.questions = [{'answer_urls': [None, None], 'answers': ['Alice', 'Bob'],
      'choice_type': 'approval', 'max': 1, 'min': 0, 'question': 'President?',
      'result_type': 'absolute', 'short_name': 'President', 'tally_type': 'homomorphic'}]
    self.election.generate_trustee(views.ELGAMAL_PARAMS)
    self.election.save()
    self.election.freeze()
    self.base = f'/helios/elections/{self.election.uuid}'
    return self.client.get(self.base + '/ui/ballot').json()

  def ui_ballot(self, ballot):
    app = Path(__file__).resolve().parents[2] / 'ALU_Election_App'
    if not (app / 'scripts/test-helios-ui.mjs').exists() or not (app / 'node_modules/jsdom').exists():
      self.skipTest('Actual React DOM integration requires the sibling frontend and its development dependencies.')
    result = subprocess.run(['node', str(app / 'scripts/test-helios-ui.mjs')],
      input=json.dumps({'ballot': ballot, 'election': json.loads(ballot['raw'])}),
      text=True, capture_output=True, timeout=180, cwd=app)
    self.assertEqual(result.returncode, 0, result.stderr[-3000:])
    return json.loads(result.stdout)

  def server_ballot(self):
    vote = homomorphic.EncryptedVote.fromElectionAndAnswers(self.election, [[1]])
    raw = vote.ld_object.serialize()
    from helios.crypto.utils import hash_b64
    return {'encrypted': raw, 'tracker': hash_b64(raw)}

  def test_actual_candidate_ui_encrypts_casts_verifies_and_tallies(self):
    ballot = self.frozen_ballot()
    result = self.ui_ballot(ballot)
    self.assertGreaterEqual(result['checks'], 12)
    vote = result['encrypted']
    parsed = datatypes.LDObject.fromDict(json.loads(vote), type_hint='legacy/EncryptedVote')
    self.assertTrue(parsed.wrapped_obj.verify(self.election))
    self.assertEqual(self.client.post(self.base + '/ui/submit', {'encrypted_vote': vote},
      HTTP_ORIGIN='https://alu.example').status_code, 302)
    # Ciphertext handoff itself neither registers nor casts a ballot.
    self.assertEqual(self.election.voter_set.count(), 0)
    self.assertEqual(models.CastVote.objects.count(), 0)
    self.assertEqual(self.client.get(self.base + '/cast_confirm').status_code, 200)
    self.assertEqual(self.client.get(self.base + '/ui/login').status_code, 302)
    pending = self.begin()
    self.assertEqual(pending['return_path'], self.base + '/cast_confirm')
    self.assertEqual(self.finish(pending)[0].status_code, 200)
    confirm = self.client.get(self.base + '/cast_confirm')
    self.assertContains(confirm, 'Submit your vote')
    self.assertNotContains(confirm, result['tracker'])
    self.assertEqual(self.election.voter_set.count(), 1)
    self.assertEqual(self.client.post(self.base + '/cast_confirm', {}).status_code, 400)
    self.assertEqual(models.CastVote.objects.count(), 0)
    token = self.client.session['csrf_token']
    self.assertEqual(self.client.post(self.base + '/cast_confirm', {'csrf_token': token}).status_code, 302)
    cast = models.CastVote.objects.get()
    self.assertIsNotNone(cast.verified_at)
    self.assertEqual(cast.vote_hash, result['tracker'])
    models.AluElectionBinding.objects.create(uuid=self.election.uuid, election=self.election, client_id=settings.ALU_BRIDGE_CLIENT_ID)
    running = self.management('stats', self.election.uuid, subject='organizer').json()
    self.assertEqual(running['votes'], 1)
    self.assertEqual([c['votes'] for c in running['positions'][0]['candidates']], [0, 1])
    self.election.refresh_from_db()
    self.assertIsNone(self.election.encrypted_tally)
    self.assertIsNone(self.election.result)
    self.assertFalse(self.election.voting_has_stopped())
    done = self.client.get(self.base + '/cast_done')
    self.assertEqual(done.url, 'https://alu.example/vote/' + self.election.uuid)
    receipt = self.client.get(self.base + '/ui/receipt/' + result['tracker']).json()
    self.assertEqual(receipt['status'], 'verified')
    self.assertFalse(receipt['released'])
    # Existing organizer authorization and unchanged eager cryptographic tally.
    self.client = Client()
    self.finish(self.begin(), subject='organizer', email='organizer@alustudent.com', access_kind='committee')
    token = self.client.session['csrf_token']
    for endpoint in ('compute_tally', 'combine_decryptions', 'release_result'):
      self.assertEqual(self.client.post(self.base + '/' + endpoint, {'csrf_token': token}).status_code, 302)
    self.assertEqual(self.client.get(self.base + '/result').json(), [[0, 1]])
    self.assertTrue(self.client.get(self.base + '/ui/ballot').json()['released'])

  def test_handoff_rejects_plaintext_origin_forgery_and_wrong_election(self):
    ballot = self.frozen_ballot()
    result = self.server_ballot()
    raw = result['encrypted']
    for origin in ('https://attacker.example', '', 'null'):
      self.assertEqual(self.client.post(self.base + '/ui/submit', {'encrypted_vote': raw}, HTTP_ORIGIN=origin).status_code, 403)
    for mutate in (lambda v: v.update(identity={'email': 'fake@alustudent.com'}),
                   lambda v: v.update(election_uuid='other'),
                   lambda v: v['answers'][0].update(answer=[1]),
                   lambda v: v['answers'][0].update(randomness=['secret'])):
      data = json.loads(raw); mutate(data)
      self.assertEqual(self.client.post(self.base + '/ui/submit', {'encrypted_vote': json.dumps(data)}, HTTP_ORIGIN='https://alu.example').status_code, 403)
    self.assertEqual(models.CastVote.objects.count(), 0)

  def test_existing_or_new_committee_session_cannot_use_ui_handoff(self):
    ballot = self.frozen_ballot()
    result = self.server_ballot()
    self.finish(self.begin())
    self.committee_subjects.add('student')
    self.assertEqual(self.client.post(self.base + '/ui/submit', {'encrypted_vote': result['encrypted']}, HTTP_ORIGIN='https://alu.example').status_code, 403)
    self.assertEqual(models.CastVote.objects.count(), 0)
    self.assertEqual(self.election.voter_set.count(), 0)

  def test_expired_login_renews_without_losing_prepared_vote(self):
    self.frozen_ballot()
    vote = self.server_ballot()
    self.finish(self.begin())
    session = self.client.session
    session['alu_session_expires_at'] = 1
    session.save()
    response = self.client.post(self.base + '/ui/submit',
      {'encrypted_vote': vote['encrypted']}, HTTP_ORIGIN='https://alu.example')
    self.assertEqual(response.status_code, 302)
    self.assertEqual(response.url, '/auth/alu/start/' + self.election.uuid + '/')
    self.assertEqual(self.client.session['encrypted_vote'], vote['encrypted'])
    self.assertEqual(models.CastVote.objects.count(), 0)
    self.client.get(self.base + '/ui/login')
    session = self.client.session
    session['alu_last_start'] = 0
    session.save()
    pending = self.begin()
    self.assertEqual(pending['return_path'], self.base + '/cast_confirm')
    self.finish(pending)
    self.assertContains(self.client.get(self.base + '/cast_confirm'), 'Submit my vote')
    session = self.client.session
    session['alu_session_expires_at'] = 1
    session.save()
    self.assertEqual(self.client.get(self.base + '/cast_confirm').url, self.base + '/ui/login')
    self.assertEqual(models.CastVote.objects.count(), 0)

  def test_live_count_is_committee_only_and_grouped_by_position(self):
    self.frozen_ballot()
    models.AluElectionBinding.objects.create(uuid=self.election.uuid, election=self.election, client_id=settings.ALU_BRIDGE_CLIENT_ID)
    result = self.management('stats', self.election.uuid, subject='organizer')
    self.assertEqual(result.status_code, 200)
    self.assertEqual(result.json()['positions'], [{'name': 'President', 'candidates': [{'name': 'Alice', 'votes': 0}, {'name': 'Bob', 'votes': 0}]}])
    self.assertEqual(result.json()['counts_status'], 'available')
    self.assertEqual(self.client.post('/helios/alu/manage', '{}', content_type='application/json').status_code, 401)
    self.assertEqual(self.management('stats', self.election.uuid, subject='student').status_code, 403)

  def test_live_counts_do_not_bypass_external_trustee_keys(self):
    self.frozen_ballot()
    trustee = self.election.trustee_set.get()
    trustee.secret_key = None
    trustee.save()
    models.AluElectionBinding.objects.create(uuid=self.election.uuid, election=self.election, client_id=settings.ALU_BRIDGE_CLIENT_ID)
    result = self.management('stats', self.election.uuid, subject='organizer').json()
    self.assertIsNone(result['positions'])
    self.assertEqual(result['counts_status'], 'keys_unavailable')

  def test_stale_login_for_another_election_renews_at_handoff(self):
    self.frozen_ballot()
    vote = self.server_ballot()
    self.finish(self.begin())
    session = self.client.session
    session['alu_election'] = str(uuid.uuid4())
    session.save()
    response = self.client.post(self.base + '/ui/submit',
      {'encrypted_vote': vote['encrypted']}, HTTP_ORIGIN='https://alu.example')
    self.assertEqual(response.status_code, 302)
    self.assertEqual(response.url, '/auth/alu/start/' + self.election.uuid + '/')
    self.assertEqual(self.client.session['encrypted_vote'], vote['encrypted'])
    self.assertEqual(models.CastVote.objects.count(), 0)

  def test_submitted_choices_for_all_positions_cannot_be_replaced(self):
    self.election.questions = [
      {'answer_urls': [None, None], 'answers': ['Alice', 'Bob'],
       'choice_type': 'approval', 'max': 1, 'min': 0, 'question': title,
       'result_type': 'absolute', 'short_name': title, 'tally_type': 'homomorphic'}
      for title in ('President', 'Vice President')]
    self.election.generate_trustee(views.ELGAMAL_PARAMS)
    self.election.save()
    self.election.freeze()
    self.base = f'/helios/elections/{self.election.uuid}'
    self.finish(self.begin())
    original = homomorphic.EncryptedVote.fromElectionAndAnswers(self.election, [[0], [1]]).ld_object.serialize()
    replacement = homomorphic.EncryptedVote.fromElectionAndAnswers(self.election, [[1], [0]]).ld_object.serialize()
    self.client.post(self.base + '/ui/submit', {'encrypted_vote': original}, HTTP_ORIGIN='https://alu.example')
    self.client.get(self.base + '/cast_confirm')
    token = self.client.session['csrf_token']
    with patch('helios.views.tasks.cast_vote_verify_and_store.delay'):
      accepted = self.client.post(self.base + '/cast_confirm', {'csrf_token': token})
      self.assertEqual(accepted.url, 'https://alu.example/vote/' + self.election.uuid)
      self.assertEqual(models.CastVote.objects.count(), 1)
      # A pending submission is locked too, before the worker verifies it.
      self.client.post(self.base + '/ui/submit', {'encrypted_vote': replacement}, HTTP_ORIGIN='https://alu.example')
      session = self.client.session
      session['encrypted_vote'] = replacement
      session.save()
      self.client.post(self.base + '/cast_confirm', {'csrf_token': token})
    self.assertEqual(models.CastVote.objects.count(), 1)
    cast = models.CastVote.objects.get()
    models.AluElectionBinding.objects.create(uuid=self.election.uuid, election=self.election, client_id=settings.ALU_BRIDGE_CLIENT_ID)
    pending_counts = self.management('stats', self.election.uuid, subject='organizer').json()
    self.assertEqual(pending_counts['votes'], 0)
    self.assertEqual(pending_counts['pending'], 1)
    self.assertEqual([[c['votes'] for c in p['candidates']] for p in pending_counts['positions']], [[0, 0], [0, 0]])
    self.assertTrue(cast.verify_and_store())
    live = self.management('stats', self.election.uuid, subject='organizer').json()
    self.assertEqual([p['name'] for p in live['positions']], ['President', 'Vice President'])
    self.assertEqual([[c['votes'] for c in p['candidates']] for p in live['positions']], [[1, 0], [0, 1]])
    self.assertEqual(live['votes'], 1)
    self.election.refresh_from_db()
    self.assertIsNone(self.election.encrypted_tally)
    self.assertIsNone(self.election.result)
    retained = cast.vote_hash
    self.client.post(self.base + '/cast', {'encrypted_vote': replacement})
    self.client.post(self.base + '/cast_confirm', {'csrf_token': token})
    self.assertEqual(models.CastVote.objects.count(), 1)
    cast.voter.refresh_from_db()
    self.assertEqual(cast.voter.vote_hash, retained)
    self.assertEqual(cast.vote.ld_object.serialize(), original)

  def test_administrator_cannot_remove_a_submitted_vote(self):
    self.frozen_ballot()
    self.finish(self.begin())
    vote = self.server_ballot()
    self.client.post(self.base + '/ui/submit', {'encrypted_vote': vote['encrypted']}, HTTP_ORIGIN='https://alu.example')
    self.client.get(self.base + '/cast_confirm')
    self.client.post(self.base + '/cast_confirm', {'csrf_token': self.client.session['csrf_token']})
    cast = models.CastVote.objects.get()
    self.client = Client()
    self.finish(self.begin(), subject='organizer', email='organizer@alustudent.com', access_kind='committee')
    response = self.client.post(self.base + '/voters/' + cast.voter.uuid + '/delete',
      {'csrf_token': self.client.session['csrf_token']})
    self.assertEqual(response.status_code, 403)
    self.assertEqual(models.CastVote.objects.count(), 1)

  def test_vote_status_requires_server_auth_and_returns_no_tracker(self):
    self.frozen_ballot()
    endpoint = self.base + '/ui/vote-status'
    body = json.dumps({'client_id': settings.ALU_BRIDGE_CLIENT_ID, 'subject': 'student'})
    self.assertEqual(self.client.post(endpoint, body, content_type='application/json').status_code, 401)
    headers = {'HTTP_AUTHORIZATION': 'Bearer ' + settings.ALU_BRIDGE_SECRET}
    self.assertEqual(self.client.post(endpoint, body, content_type='application/json', **headers).json(),
      {'election_id': self.election.uuid, 'status': 'none'})
    self.finish(self.begin())
    vote = self.server_ballot()
    self.client.post(self.base + '/ui/submit', {'encrypted_vote': vote['encrypted']}, HTTP_ORIGIN='https://alu.example')
    self.client.get(self.base + '/cast_confirm')
    with patch('helios.views.tasks.cast_vote_verify_and_store.delay'):
      self.client.post(self.base + '/cast_confirm', {'csrf_token': self.client.session['csrf_token']})
    self.assertEqual(self.client.post(endpoint, body, content_type='application/json', **headers).json()['status'], 'pending')
    self.assertTrue(models.CastVote.objects.get().verify_and_store())
    self.assertEqual(self.client.post(endpoint, body, content_type='application/json', **headers).json(),
      {'election_id': self.election.uuid, 'status': 'verified'})

  def test_private_or_unallowlisted_ballot_not_exposed(self):
    self.frozen_ballot()
    self.election.private_p = True; self.election.save()
    self.assertNotEqual(self.client.get(self.base + '/ui/ballot').status_code, 200)
    self.assertNotEqual(self.client.get(self.base + '/ui/receipt/' + 'a'*43).status_code, 200)

  def management(self, operation, election_id, subject='new-chair', **payload):
    import requests
    original = requests.post
    def fresh_access(url, **kwargs):
      if not url.endswith('/api/helios/manage-access'):
        return original(url, **kwargs)
      data = kwargs['json']
      response = Mock(status_code=200)
      response.json.return_value = {'authorized': True,
        'binding': {key: data[key] for key in ('subject', 'election_id', 'operation')},
        'identity': {'subject': subject, 'email': subject + '@alustudent.com',
                     'email_verified': True, 'name': 'Chair'}}
      return response
    with patch('helios.alu_management.requests.post', side_effect=fresh_access):
      return self.client.post('/helios/alu/manage', json.dumps({
        'client_id': settings.ALU_BRIDGE_CLIENT_ID, 'election_id': election_id,
        'subject': subject, 'operation': operation, **payload}), content_type='application/json',
        HTTP_AUTHORIZATION='Bearer ' + settings.ALU_BRIDGE_SECRET)

  def test_malformed_management_inputs_fail_before_network(self):
    headers = {'HTTP_AUTHORIZATION': 'Bearer ' + settings.ALU_BRIDGE_SECRET}
    base = {'client_id': settings.ALU_BRIDGE_CLIENT_ID, 'election_id': str(uuid.uuid4()),
            'subject': 'new-chair', 'operation': 'create', 'name': 'TEST malformed'}
    bodies = ['[]', 'null', 'true', '[' * 1100 + '0' + ']' * 1100,
              json.dumps({**base, 'subject': ['forged']}),
              json.dumps({**base, 'operation': {'create': True}}),
              json.dumps(base)[:-1] + ',"subject":"substituted"}']
    with patch('helios.alu_management.requests.post') as network:
      for body in bodies:
        with self.subTest(body_type=body[:20]):
          response = self.client.post('/helios/alu/manage', body,
            content_type='application/json', **headers)
          self.assertEqual(response.status_code, 400)
          self.assertEqual(response['Cache-Control'], 'no-store')
      network.assert_not_called()

  def test_creation_and_ballot_freeze_preserve_permissions_and_crypto(self):
    election_id = str(uuid.uuid4())
    self.assertEqual(self.client.post('/helios/alu/manage', 'invalid',
      content_type='application/json').status_code, 401)
    created = self.management('create', election_id, name='TEST from existing creation UI')
    self.assertEqual(created.status_code, 200)
    for premature in ('tally', 'combine', 'release'):
      self.assertEqual(self.management(premature, election_id).status_code, 403)
    self.assertEqual(self.management('create', election_id, name='Replay').status_code, 200)
    self.assertEqual(models.Election.objects.filter(uuid=election_id).count(), 1)
    owner = models.User.objects.get(user_id='new-chair')
    self.assertFalse(owner.admin_p)
    election = models.Election.get_by_uuid(election_id)
    self.assertEqual(election.admin, owner)
    self.assertFalse(views.user_can_admin_election(owner, self.election))
    self.assertEqual(self.management('ballot', election_id, subject='different-chair',
      name='Attack', seats=[{'title':'President', 'answers':['Alice']}]).status_code, 403)
    synced = self.management('ballot', election_id, name='TEST from creation UI',
      seats=[{'title': 'President', 'answers': ['Alice', 'Bob']}])
    self.assertEqual(synced.status_code, 200)
    self.assertEqual(self.management('freeze', election_id, setup_digest='0'*64).status_code, 403)
    frozen = self.management('freeze', election_id, setup_digest=synced.json()['setup_digest'])
    self.assertEqual(frozen.status_code, 200)
    self.assertTrue(frozen.json()['frozen'])
    for premature in ('combine', 'release'):
      self.assertEqual(self.management(premature, election_id).status_code, 403)
    self.assertEqual(self.management('ballot', election_id, name='Attack',
      seats=[{'title':'President', 'answers':['Replacement']}]).status_code, 403)
    self.assertEqual(self.client.get(f'/helios/elections/{election_id}/ui/ballot').status_code, 200)
    self.assertEqual(self.client.get('/auth/alu/start/' + election_id + '/').status_code, 302)
    self.assertEqual(self.client.get(f'/helios/elections/{election_id}/password_voter_login').status_code, 403)
    self.client = Client()
    election.refresh_from_db()
    self.election = election
    self.finish(self.begin())
    vote = self.server_ballot()
    base = '/helios/elections/' + election_id
    self.assertEqual(self.client.post(base + '/ui/submit', {'encrypted_vote': vote['encrypted']},
      HTTP_ORIGIN='https://alu.example').status_code, 302)
    self.assertEqual(self.client.get(base + '/cast_confirm').status_code, 200)
    self.assertEqual(self.client.post(base + '/cast_confirm',
      {'csrf_token': self.client.session['csrf_token']}).status_code, 302)
    self.assertEqual(self.management('tally', election_id).status_code, 200)
    self.assertEqual(self.management('combine', election_id).status_code, 200)
    self.assertEqual(self.management('release', election_id).status_code, 200)
    self.assertEqual(self.client.get(base + '/ui/ballot').json()['result'], [[0, 1]])

  def test_scheduled_and_manual_start_preserve_frozen_ballot_and_deadline(self):
    import datetime
    election_id = str(uuid.uuid4())
    self.assertEqual(self.management('create', election_id, name='Scheduled election').status_code, 200)
    now = datetime.datetime.utcnow()
    start = now + datetime.timedelta(days=2)
    end = now + datetime.timedelta(days=3)
    synced = self.management('ballot', election_id, name='Scheduled election',
      seats=[{'title':'President','answers':['Alice','Bob']}],
      voting_starts_at=start.isoformat()+'Z', voting_ends_at=end.isoformat()+'Z')
    digest = synced.json()['setup_digest']
    frozen = self.management('freeze', election_id, setup_digest=digest, start_now=False)
    self.assertEqual(frozen.status_code, 200)
    self.assertFalse(frozen.json()['open'])
    base = f'/helios/elections/{election_id}/ui/ballot'
    before = self.client.get(base).json()
    self.assertFalse(before['open'])
    with patch('helios.models.datetime.datetime') as clock:
      clock.utcnow.return_value = start + datetime.timedelta(seconds=1)
      self.assertTrue(models.Election.get_by_uuid(election_id).voting_has_started())
    self.assertEqual(self.management('freeze', election_id, subject='wrong', setup_digest=digest, start_now=True).status_code, 403)
    opened = self.management('freeze', election_id, setup_digest=digest, start_now=True)
    self.assertEqual(opened.status_code, 200)
    self.assertTrue(opened.json()['open'])
    election = models.Election.get_by_uuid(election_id)
    actual = election.voting_started_at
    self.assertIsNotNone(actual)
    self.assertEqual(election.voting_starts_at,start)
    self.assertEqual(election.voting_ends_at,end)
    self.assertEqual(before['raw'],self.client.get(base).json()['raw'])
    self.assertEqual(self.management('freeze', election_id, setup_digest=digest, start_now=True).status_code, 200)
    self.assertEqual(models.Election.get_by_uuid(election_id).voting_started_at,actual)
    election.voting_ended_at=now-datetime.timedelta(seconds=1);election.save()
    self.assertEqual(self.management('freeze', election_id, setup_digest=digest, start_now=True).status_code,403)
    self.assertEqual(self.management('freeze', election_id, setup_digest=digest, start_now='true').status_code,400)

# A real PostgreSQL transaction test ensures two simultaneous confirmations
# reserve only one submission before the verification task runs.


@override_settings(AUTH_ENABLED_SYSTEMS=['alu'], ALU_STUDENT_DOMAIN='alustudent.com',
  ALU_BRIDGE_APP_ORIGIN='https://alu.example', SECURE_URL_HOST='https://helios.example',
  ALU_BRIDGE_SECRET='test-only-secret-with-at-least-32-bytes',
  ALU_BRIDGE_CLIENT_ID='alu-helios-demo', CELERY_TASK_ALWAYS_EAGER=True,
  CELERY_BROKER_URL='memory://', EMAIL_BACKEND='django.core.mail.backends.dummy.EmailBackend')
class AluSingleSubmissionTests(TransactionTestCase):
  setUp = test_bridge.BridgeTests.setUp
  begin = test_bridge.BridgeTests.begin
  finish = test_bridge.BridgeTests.finish
  frozen_ballot = AluUiTests.frozen_ballot
  server_ballot = AluUiTests.server_ballot

  def test_concurrent_confirmations_keep_only_one_submission(self):
    self.frozen_ballot()
    self.finish(self.begin())
    original = self.server_ballot()['encrypted']
    self.client.post(self.base + '/ui/submit', {'encrypted_vote': original}, HTTP_ORIGIN='https://alu.example')
    self.client.get(self.base + '/cast_confirm')
    second = Client()
    self.finish(self.begin(client=second), client=second)
    second.post(self.base + '/ui/submit', {'encrypted_vote': original}, HTTP_ORIGIN='https://alu.example')
    barrier = Barrier(2)
    thread = local()
    original_access = views.require_voting_access
    def synchronized_access(*args):
      original_access(*args)
      thread.checks = getattr(thread, 'checks', 0) + 1
      if thread.checks == 2:
        barrier.wait(timeout=10)
    def submit(client):
      close_old_connections()
      try:
        return client.post(self.base + '/cast_confirm', {'csrf_token': client.session['csrf_token']}).status_code
      finally:
        connections.close_all()
    with patch('helios.views.require_voting_access', side_effect=synchronized_access), \
         patch('helios.views.tasks.cast_vote_verify_and_store.delay') as verification:
      with ThreadPoolExecutor(max_workers=2) as pool:
        self.assertEqual(list(pool.map(submit, [self.client, second])), [302, 302])
      self.assertEqual(verification.call_count, 1)
    self.assertEqual(models.CastVote.objects.count(), 1)
