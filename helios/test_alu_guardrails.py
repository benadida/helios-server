from django.test import TransactionTestCase, RequestFactory
from django.db import connections, close_old_connections, DatabaseError
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from helios.models import AluRateBucket
from django.http import HttpResponse
from helios.alu_guardrails import AluRequestGuardrails


class AluGuardrailTests(TransactionTestCase):
    def setUp(self):
        AluRateBucket.objects.all().delete()
        self.factory = RequestFactory()
        self.middleware = AluRequestGuardrails(lambda request: HttpResponse('ok'))

    def request(self, subject='student', **meta):
        request = self.factory.post('/helios/elections/test/cast', **meta)
        request.session = {'alu_election': 'test', 'user': {'type': 'alu', 'user_id': subject}}
        return request

    def test_repeated_casts_are_limited_per_account(self):
        for _ in range(20):
            self.assertEqual(self.middleware(self.request()).status_code, 200)
        refused = self.middleware(self.request())
        self.assertEqual(refused.status_code, 429)
        self.assertEqual(refused['Retry-After'], '60')
        self.assertEqual(self.middleware(self.request('other-student')).status_code, 200)

    def test_forwarded_headers_cannot_bypass_account_limit(self):
        for _ in range(20):
            self.middleware(self.request())
        self.assertEqual(self.middleware(self.request(HTTP_X_FORWARDED_FOR='different')).status_code, 429)

    def test_oversized_or_invalid_request_refused(self):
        self.assertEqual(self.middleware(self.request(CONTENT_LENGTH=str(2097153))).status_code, 413)
        self.assertEqual(self.middleware(self.request(CONTENT_LENGTH='invalid')).status_code, 400)

    def test_reading_receipts_is_not_throttled(self):
        for _ in range(25):
            self.assertEqual(self.middleware(self.factory.get('/helios/elections/test/ui/receipt/tracker')).status_code, 200)

    def test_concurrent_workers_share_one_atomic_limit(self):
        def attempt(_):
            close_old_connections()
            try:
                middleware = AluRequestGuardrails(lambda request: HttpResponse('ok'))
                return middleware(self.request()).status_code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(pool.map(attempt, range(32)))
        self.assertEqual(statuses.count(200), 20)
        self.assertEqual(statuses.count(429), 12)
        self.assertEqual(AluRateBucket.objects.get().hits, 20)

    def test_database_failure_is_closed(self):
        with patch('helios.alu_guardrails.connection.cursor', side_effect=DatabaseError):
            self.assertEqual(self.middleware(self.request()).status_code, 503)

    def test_expired_buckets_are_cleaned_without_identity_storage(self):
        from django.utils import timezone
        import datetime
        AluRateBucket.objects.create(key='expired', hits=1,
            expires_at=timezone.now()-datetime.timedelta(minutes=1))
        self.assertEqual(self.middleware(self.request()).status_code, 200)
        self.assertFalse(AluRateBucket.objects.filter(key='expired').exists())
        self.assertNotIn('student', AluRateBucket.objects.get().key)
