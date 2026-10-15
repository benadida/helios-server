import datetime
import json
import uuid
from unittest.mock import Mock, patch
from django.conf import settings
from django.db import connection
from django.test import TestCase, override_settings
from helios import models
from helios.alu_report import operational_report
from helios_auth.models import User

@override_settings(ALU_BRIDGE_SECRET='report-test-secret-with-at-least-thirty-two-bytes',
                   ALU_BRIDGE_APP_ORIGIN='https://alu.example', ALU_BRIDGE_CLIENT_ID='alu-helios-demo')
class ProcessReportTests(TestCase):
    def setUp(self):
        self.actor=User.objects.create(user_type='alu',user_id='chair',name='Chair',info={})
        self.election=models.Election.objects.create(admin=self.actor,uuid=str(uuid.uuid4()),short_name='report-'+str(uuid.uuid4()),name='Report test')
        models.AluElectionBinding.objects.create(election=self.election,uuid=self.election.uuid,client_id='alu-helios-demo')

    def voters(self,count,day):
        for i in range(count):
            voter=models.Voter.objects.create(election=self.election,uuid=str(uuid.uuid4()),voter_login_id=str(uuid.uuid4()))
            # Opaque fake ciphertext: reporting must never deserialize it.
            with connection.cursor() as q:
                q.execute("update helios_voter set vote=%s,cast_at=%s where id=%s",['PRIVATE-CIPHERTEXT',day,voter.pk])

    def test_live_series_and_ballot_identity_are_never_exposed(self):
        self.voters(5,datetime.datetime(2026,10,14,10))
        data=operational_report(self.election,False)
        self.assertIsNone(data['vote_days'])
        self.assertEqual(data['vote_days_status'],'voting_not_closed')
        serialized=json.dumps(data)
        for secret in ['PRIVATE-CIPHERTEXT','vote_hash','cast_ip','voter_login_id','chair']:
            self.assertNotIn(secret,serialized)

    def test_any_small_day_suppresses_entire_series(self):
        self.voters(5,datetime.datetime(2026,10,14,10))
        self.voters(1,datetime.datetime(2026,10,15,10))
        data=operational_report(self.election,True)
        self.assertIsNone(data['vote_days'])
        self.assertEqual(data['vote_days_status'],'small_groups')

    def test_closed_series_uses_kigali_days_without_precise_timestamps(self):
        self.voters(5,datetime.datetime(2026,10,14,23,30))
        data=operational_report(self.election,True)
        self.assertEqual(data['vote_days'],[{'day':'2026-10-15','votes':5}])
        self.assertIsNone(data['verification_seconds'])

    def test_management_authentication_and_independent_permission_check(self):
        payload={'operation':'report','subject':'chair','client_id':'alu-helios-demo','election_id':self.election.uuid}
        url='/helios/alu/manage'
        self.assertEqual(self.client.post(url,json.dumps(payload),content_type='application/json').status_code,401)
        denied=Mock(status_code=403);denied.json.return_value={}
        with patch('helios.alu_management.requests.post',return_value=denied):
            self.assertEqual(self.client.post(url,json.dumps(payload),content_type='application/json',HTTP_AUTHORIZATION='Bearer '+settings.ALU_BRIDGE_SECRET).status_code,403)
        approved=Mock(status_code=200);approved.json.return_value={'authorized':True,'binding':{k:payload[k] for k in ['subject','election_id','operation']},'identity':{'subject':'chair','email':'chair@alustudent.com','email_verified':True}}
        with patch('helios.alu_management.requests.post',return_value=approved):
            response=self.client.post(url,json.dumps(payload),content_type='application/json',HTTP_AUTHORIZATION='Bearer '+settings.ALU_BRIDGE_SECRET)
        self.assertEqual(response.status_code,200)
        self.assertIn('report',response.json())
        self.assertEqual(response['Cache-Control'],'no-store')

    @override_settings(RECOVERY_SECRET='test-lifecycle-secret')
    def test_lifecycle_future_open_closed_published_and_overlapping_elections(self):
        from helios.runtime_health import verification_state
        from django.test import RequestFactory
        def state():
            request=RequestFactory().get('/internal/verification-state',HTTP_AUTHORIZATION='Bearer test-lifecycle-secret')
            return json.loads(verification_state(request).content)
        now=datetime.datetime.utcnow()
        self.assertFalse(state()['keep_alive'])
        self.election.frozen_at=now
        self.election.voting_starts_at=now+datetime.timedelta(days=1)
        self.election.save()
        self.assertFalse(state()['keep_alive'])
        self.assertEqual(state()['next_wake_at'],int((self.election.voting_starts_at-datetime.timedelta(minutes=5)).replace(tzinfo=datetime.timezone.utc).timestamp()*1000))
        self.election.voting_started_at=now;self.election.save()
        self.assertTrue(state()['keep_alive'])
        self.election.voting_ended_at=now;self.election.save()
        self.assertTrue(state()['keep_alive'])
        other=models.Election.objects.create(admin=self.actor,uuid=str(uuid.uuid4()),short_name='overlap',name='Overlap',frozen_at=now,voting_started_at=now)
        self.election.result_released_at=now;self.election.save()
        self.assertTrue(state()['keep_alive'])
        other.result_released_at=now;other.save()
        self.assertFalse(state()['keep_alive'])
        self.assertIsNone(state()['next_wake_at'])
        # Frozen elections without a start date are immediately open in Helios.
        immediate=models.Election.objects.create(admin=self.actor,uuid=str(uuid.uuid4()),short_name='immediate',name='Immediate',frozen_at=now)
        self.assertTrue(state()['keep_alive'])
        immediate.result_released_at=now;immediate.save()
        voter=models.Voter.objects.create(election=immediate,uuid=str(uuid.uuid4()),voter_login_id='pending-test')
        with connection.cursor() as q:
            q.execute("insert into helios_castvote(vote,vote_hash,cast_at,quarantined_p,voter_id) values(%s,%s,%s,%s,%s) returning id",['opaque-test-ciphertext','test-hash',now,False,voter.id])
            cast_id=q.fetchone()[0]
        job=models.VoteVerificationJob.objects.create(cast_vote_id=cast_id)
        self.assertTrue(state()['keep_alive'])
        job.state='failed';job.save()
        self.assertTrue(state()['keep_alive'])
        self.assertTrue(state()['needs_attention'])
        job.state='complete';job.save()
        self.assertFalse(state()['keep_alive'])


    def test_eligibility_batches_are_bounded_and_fail_closed(self):
        import threading,time
        from helios.bridge_eligibility import statuses
        from django.core.exceptions import PermissionDenied
        voters=[{'subject':str(i),'cast_at':None} for i in range(250)]
        lock=threading.Lock();active=0;peak=0
        def request(url,**kwargs):
            nonlocal active,peak
            with lock:active+=1;peak=max(peak,active)
            time.sleep(.01)
            batch=kwargs['json']['voters']
            with lock:active-=1
            response=Mock(status_code=200)
            response.json.return_value={'binding':{'client_id':'alu-helios-demo','election_id':self.election.uuid},'voters':[{'subject':v['subject'],'student':True,'committee':False,'events':[]} for v in batch]}
            return response
        with patch('helios.bridge_eligibility.requests.post',side_effect=request) as post:
            result=statuses(self.election,voters)
        self.assertEqual(len(result),250);self.assertEqual(post.call_count,5)
        self.assertGreater(peak,1);self.assertLessEqual(peak,4)
        with patch('helios.bridge_eligibility.requests.post',return_value=Mock(status_code=503)):
            with self.assertRaises(PermissionDenied):statuses(self.election,voters)
