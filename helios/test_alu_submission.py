"""Real encrypted acceptance, recovery and email outbox on isolated PostgreSQL."""
import datetime
import json
import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch
from django.db import OperationalError, close_old_connections, connections
from django.test import Client, TransactionTestCase, override_settings
from helios import models
from helios import test_alu_ui as ui_fixtures
from helios_auth import test_bridge as auth_fixtures
from helios_auth.bridge_protocol import challenge
from helios.vote_verification import process_next_job
from helios.vote_confirmation import deliver_next_confirmation

@override_settings(**(auth_fixtures.BridgeTests._overridden_settings | {'ALU_VOTE_VERIFICATION_BACKEND':'database'}))
class SubmissionTests(TransactionTestCase):
    setUp = auth_fixtures.BridgeTests.setUp
    frozen_ballot = ui_fixtures.AluUiTests.frozen_ballot
    server_ballot = ui_fixtures.AluUiTests.server_ballot

    def payload(self):
        return {'client_id':'alu-helios-demo','code':secrets.token_urlsafe(32),
            'state':secrets.token_urlsafe(32),'verifier':secrets.token_urlsafe(48),
            'encrypted_vote':self.server_ballot()['encrypted']}

    def network(self, payload, subject='student', mutate=None):
        status_mock = __import__('requests').post
        def dispatch(url, **kwargs):
            if url.endswith('/exchange'):
                result=Mock(status_code=200)
                result.json.return_value={'identity':{'subject':subject,'email':subject+'@alustudent.com','email_verified':True,'name':'Student'},
                    'access_kind':'voter','session_expires_at':time.time()+290,
                    'binding':{'client_id':payload['client_id'],'election_id':self.election.uuid,'state':payload['state'],'code_challenge':challenge(payload['verifier'])}}
                if mutate:mutate(result.json.return_value)
                return result
            return status_mock(url,**kwargs)
        return patch('helios.alu_submission.requests.post',side_effect=dispatch)

    def submit(self,payload,client=None,secret=True):
        return (client or self.client).post(self.base+'/ui/cast',data=json.dumps(payload),content_type='application/json',
            HTTP_AUTHORIZATION='Bearer '+('test-only-secret-with-at-least-32-bytes' if secret else 'wrong'))

    def status(self):
        return self.client.post(self.base+'/ui/vote-status',data=json.dumps({'client_id':'alu-helios-demo','subject':'student'}),
            content_type='application/json',HTTP_AUTHORIZATION='Bearer test-only-secret-with-at-least-32-bytes').json()['status']

    def test_verified_outbox_and_safe_replay(self):
        self.frozen_ballot();payload=self.payload()
        with self.network(payload):
            self.assertEqual(self.submit(payload).status_code,202)
            self.assertEqual(self.submit(payload).status_code,200)
        self.assertEqual(models.CastVote.objects.count(),1)
        self.assertEqual(models.VoteVerificationJob.objects.count(),1)
        self.assertEqual(models.VoteConfirmationEmail.objects.count(),0)
        self.assertEqual(self.status(),'pending')
        self.assertTrue(process_next_job());self.assertEqual(self.status(),'verified')
        mail=models.VoteConfirmationEmail.objects.get()
        self.assertEqual(set(mail.payload),{'recipient','election_id','election_name'})
        self.assertNotIn('Bob',json.dumps(mail.payload))
        cast=models.CastVote.objects.get();cast.verify_and_store()
        self.assertEqual(models.VoteConfirmationEmail.objects.count(),1)
        with self.network(payload):self.assertEqual(self.submit(payload).json()['status'],'verified')

    def test_refusals_atomic_rollback_and_verifier_recovery(self):
        self.frozen_ballot();payload=self.payload()
        with self.network(payload):
            self.assertEqual(self.submit(payload,secret=False).status_code,401)
            self.committee_subjects.add('student')
            self.assertEqual(self.submit(payload).status_code,403)
            self.committee_subjects.clear()
            with patch('helios.vote_verification.schedule_verification',side_effect=OperationalError('synthetic')):
                with self.assertRaises(OperationalError):self.submit(payload)
            self.assertEqual(models.CastVote.objects.count(),0)
            self.assertEqual(models.VoteVerificationJob.objects.count(),0)
            self.assertEqual(self.submit(payload).status_code,202)
        job=models.VoteVerificationJob.objects.get();job.attempts=7;job.save()
        with patch('helios.tasks.cast_vote_verify_and_store',side_effect=RuntimeError('synthetic')):process_next_job()
        self.assertEqual(self.status(),'attention');self.assertEqual(models.VoteConfirmationEmail.objects.count(),0)
        job.refresh_from_db();job.attempts=0;job.state='pending';job.next_attempt_at=datetime.datetime.utcnow();job.save()
        process_next_job();self.assertEqual(self.status(),'verified')

    def test_invalid_proof_has_explicit_status_and_no_success_email(self):
        self.frozen_ballot();payload=self.payload();raw=json.loads(payload['encrypted_vote'])
        proof=raw['answers'][0]['individual_proofs'][0][0];proof['challenge']=str(int(proof['challenge'])+1)
        payload['encrypted_vote']=json.dumps(raw)
        with self.network(payload):self.assertEqual(self.submit(payload).status_code,202)
        process_next_job();self.assertEqual(self.status(),'invalid')
        self.assertEqual(models.VoteConfirmationEmail.objects.count(),0)

    def test_concurrent_first_registration_and_submission(self):
        self.frozen_ballot();payload=self.payload()
        def run(_):
            close_old_connections()
            try:return self.submit(payload,client=Client()).status_code
            finally:connections.close_all()
        with self.network(payload):
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertEqual(sorted(pool.map(run,range(2))),[200,202])
        self.assertEqual(models.CastVote.objects.count(),1)
        self.assertEqual(models.Voter.objects.count(),1)

    def test_grant_binding_expiry_and_closed_during_authentication(self):
        self.frozen_ballot();payload=self.payload()
        for mutate in [lambda g:g.update(access_kind='committee'),
                lambda g:g.update(session_expires_at=time.time()-1),
                lambda g:g['binding'].update(election_id='wrong'),
                lambda g:g['identity'].update(email_verified=False)]:
            with self.network(payload,mutate=mutate):
                self.assertEqual(self.submit(payload).status_code,403)
        def close_during_auth(grant):
            models.Election.objects.filter(pk=self.election.pk).update(voting_ended_at=datetime.datetime.utcnow())
        with self.network(payload,mutate=close_during_auth):
            self.assertEqual(self.submit(payload).status_code,409)
        self.assertEqual(models.CastVote.objects.count(),0)
        self.assertEqual(models.VoteConfirmationEmail.objects.count(),0)

    def test_confirmation_claims_once_and_verification_email_rollback(self):
        self.frozen_ballot();payload=self.payload()
        with self.network(payload):self.submit(payload)
        with patch('helios.vote_confirmation.queue_confirmation',side_effect=RuntimeError('synthetic outbox failure')):
            process_next_job()
        cast=models.CastVote.objects.get();self.assertIsNone(cast.verified_at)
        self.assertEqual(models.VoteConfirmationEmail.objects.count(),0)
        job=models.VoteVerificationJob.objects.get();job.next_attempt_at=datetime.datetime.utcnow();job.save()
        process_next_job();self.assertEqual(self.status(),'verified')
        def run(_):
            close_old_connections()
            try:return deliver_next_confirmation()
            finally:connections.close_all()
        reply=Mock(status_code=200);reply.json.return_value={'sent':True}
        with patch('helios.vote_confirmation.requests.post',return_value=reply) as send:
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertEqual(sorted(pool.map(run,range(2))),[False,True])
            self.assertEqual(send.call_count,1)
        self.assertEqual(models.VoteConfirmationEmail.objects.get().state,'sent')

    def test_confirmation_retry_and_expiry(self):
        self.frozen_ballot();payload=self.payload()
        with self.network(payload):self.submit(payload)
        process_next_job();mail=models.VoteConfirmationEmail.objects.get()
        with patch('helios.vote_confirmation.requests.post',side_effect=__import__('requests').Timeout):
            self.assertTrue(deliver_next_confirmation())
        mail.refresh_from_db();self.assertEqual(mail.state,'pending');self.assertEqual(self.status(),'verified')
        first_id=str(mail.id);mail.next_attempt_at=datetime.datetime.utcnow();mail.save()
        reply=Mock(status_code=200);reply.json.return_value={'sent':True}
        with patch('helios.vote_confirmation.requests.post',return_value=reply) as send:
            deliver_next_confirmation()
            self.assertEqual(send.call_args.kwargs['json']['id'],first_id)
            self.assertEqual(send.call_args.kwargs['json']['provider'],'sendbyte')
        mail.refresh_from_db();self.assertEqual(mail.state,'sent')
        with patch('helios.vote_confirmation.requests.post') as send:
            self.assertFalse(deliver_next_confirmation());send.assert_not_called()
        mail.state='pending';mail.next_attempt_at=datetime.datetime.utcnow();mail.first_attempt_at=datetime.datetime.utcnow()-datetime.timedelta(hours=24);mail.save()
        with patch('helios.vote_confirmation.requests.post') as send:
            deliver_next_confirmation();send.assert_not_called()
        mail.refresh_from_db();self.assertEqual(mail.state,'review_required')

    def test_confirmation_provider_switch_holds_ambiguous_deliveries(self):
        from importlib import import_module
        from types import SimpleNamespace
        from django.apps import apps
        from django.db import connection
        transfer = import_module('helios.migrations.0016_sendbyte_email_provider').transfer_unsent
        self.frozen_ballot();payload=self.payload()
        with self.network(payload):self.submit(payload)
        process_next_job();mail=models.VoteConfirmationEmail.objects.get()
        self.assertEqual(mail.provider,'sendbyte')
        for state,attempts,expected in [('pending',0,'pending'),('pending',1,'review_required'),
                                        ('sending',1,'review_required'),('sent',1,'sent')]:
            with self.subTest(state=state, attempts=attempts):
                mail.provider='resend';mail.state=state;mail.attempts=attempts
                mail.first_attempt_at=datetime.datetime.utcnow() if attempts else None
                mail.attempted_at=mail.first_attempt_at;mail.save()
                transfer(apps,SimpleNamespace(connection=connection))
                mail.refresh_from_db()
                self.assertEqual(mail.state,expected)
                self.assertEqual(mail.provider,'sendbyte' if attempts==0 else 'resend')
                if attempts:
                    with patch('helios.vote_confirmation.requests.post') as send:
                        self.assertFalse(deliver_next_confirmation());send.assert_not_called()
