"""Performance boundaries must retain authorization and durable recovery."""
import json
import select
import time
from unittest.mock import patch

from django.db import connection, transaction
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext

from helios import models
from helios import test_alu_submission as fixtures
from helios.verification_wakeup import VerificationWakeup


class VotingPerformanceTests(fixtures.SubmissionTests):
    def test_json_reads_and_acceptance_never_persist_browser_sessions(self):
        self.frozen_ballot()
        payload = self.payload()
        from helios.bridge_eligibility import service_post
        before = service_post.call_count
        with self.network(payload) as network:
            with CaptureQueriesContext(connection) as queries:
                accepted = self.submit(payload, client=Client())
            self.assertEqual(accepted.status_code, 202)
            self.assertFalse(accepted.cookies)
            endpoints = [c.args[0].rsplit('/', 1)[-1] for c in network.call_args_list]
            self.assertEqual(endpoints, ['exchange'])
            self.assertEqual(service_post.call_count - before, 1)
        self.assertFalse(any('django_session' in q['sql'] for q in queries))
        paths = [(self.base+'/ui/ballot', None),
                 (self.base+'/ui/receipt/'+'a'*43, None),
                 (self.base+'/ui/vote-status', {'client_id':'alu-helios-demo', 'subject':'student'})]
        for path, body in paths:
            with CaptureQueriesContext(connection) as queries:
                client = Client()
                response = (client.get(path) if body is None else client.post(path,
                    data=json.dumps(body), content_type='application/json',
                    HTTP_AUTHORIZATION='Bearer test-only-secret-with-at-least-32-bytes'))
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.cookies)
            self.assertFalse(any('django_session' in q['sql'] for q in queries))

    def test_status_authenticates_before_any_database_lookup(self):
        self.frozen_ballot()
        with self.assertNumQueries(0):
            self.assertEqual(Client().post(self.base+'/ui/vote-status', data='{}',
                content_type='application/json').status_code, 401)

    def test_public_json_adapters_refuse_private_unbound_and_deleted_elections(self):
        self.frozen_ballot()
        self.election.private_p = True
        self.election.save()
        self.assertEqual(Client().get(self.base+'/ui/ballot').status_code, 403)
        self.election.private_p = False
        self.election.save()
        with override_settings(ALU_BRIDGE_ELECTIONS=()):
            self.assertEqual(Client().get(self.base+'/ui/ballot').status_code, 403)
        models.Election.objects.filter(pk=self.election.pk).update(deleted_at=__import__('datetime').datetime.utcnow())
        self.assertEqual(Client().get(self.base+'/ui/ballot').status_code, 404)

    def test_final_membership_check_can_still_refuse_before_commit(self):
        self.frozen_ballot()
        payload = self.payload()
        # Exchange succeeds, but membership changes before the final callback.
        with self.network(payload, mutate=lambda grant:self.committee_subjects.add('student')):
            self.assertEqual(self.submit(payload).status_code, 403)
        self.assertFalse(models.CastVote.objects.exists())
        self.assertFalse(models.VoteVerificationJob.objects.exists())

    def test_wakeup_is_empty_and_visible_only_after_commit(self):
        self.frozen_ballot()
        payload = self.payload()
        wakeup = VerificationWakeup()
        wakeup.connect()
        self.addCleanup(wakeup.close)
        self.assertIsNotNone(wakeup.listener)
        raw = wakeup.listener.connection
        # A rollback neither accepts a vote nor wakes the verifier.
        with self.network(payload), transaction.atomic():
            self.assertEqual(self.submit(payload).status_code, 202)
            self.assertFalse(select.select([raw], [], [], 0)[0])
            transaction.set_rollback(True)
        self.assertFalse(select.select([raw], [], [], 0.02)[0])
        self.assertFalse(models.VoteVerificationJob.objects.exists())
        with self.network(payload):
            self.assertEqual(self.submit(payload).status_code, 202)
        self.assertTrue(select.select([raw], [], [], 1)[0])
        raw.poll()
        self.assertTrue(raw.notifies)
        self.assertTrue(all(n.payload == '' for n in raw.notifies))
        started = time.monotonic()
        wakeup.wait(2)
        self.assertLess(time.monotonic()-started, 0.2)
        # Missing wake hints do not affect durable processing.
        wakeup.close()
        from helios.vote_verification import process_next_job
        self.assertTrue(process_next_job())
        self.assertEqual(self.status(), 'verified')

    def test_listener_failure_retains_bounded_polling(self):
        wakeup = VerificationWakeup()
        with patch('helios.verification_wakeup.connections') as connections:
            listener = connections.__getitem__.return_value.copy.return_value
            listener.ensure_connection.side_effect = RuntimeError('synthetic')
            wakeup.connect()
            self.assertIsNone(wakeup.listener)
            listener.close.assert_called_once()
        with patch('helios.verification_wakeup.time.sleep') as sleep:
            wakeup.wait(2)
            sleep.assert_called_once_with(2)
