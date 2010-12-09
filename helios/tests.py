"""
Unit Tests for Helios
"""

import unittest, datetime

import models
from auth import models as auth_models
from views import ELGAMAL_PARAMS

from django.db import IntegrityError, transaction

from django.test.client import Client
from django.test import TestCase

from django.core import mail

import uuid

class ElectionModelTests(TestCase):
    fixtures = ['users.json']

    def create_election(self):
        return models.Election.get_or_create(
            short_name='demo',
            name='Demo Election',
            description='Demo Election Description',
            admin=self.user)

    def setup_questions(self):
        QUESTIONS = [{"answer_urls": [None, None, None], "answers": ["a", "b", "c"], "choice_type": "approval", "max": 1, "min": 0, "question": "w?", "result_type": "absolute", "short_name": "w?", "tally_type": "homomorphic"}]
        self.election.questions = QUESTIONS

    def setup_trustee(self):
        self.election.generate_trustee(ELGAMAL_PARAMS)
    
    def setUp(self):
        self.user = auth_models.User.objects.get(user_id='ben@adida.net', user_type='google')
        self.election, self.created_p = self.create_election()

    def test_create_election(self):
        # election should be created
        self.assertTrue(self.created_p)

        # should have a creation time
        self.assertNotEquals(self.election.created_at, None)
        self.assertTrue(self.election.created_at < datetime.datetime.utcnow())

    def test_find_election(self):
        election = models.Election.get_by_user_as_admin(self.user)[0]
        self.assertEquals(self.election, election)

        election = models.Election.get_by_uuid(self.election.uuid)
        self.assertEquals(self.election, election)

        election = models.Election.get_by_short_name(self.election.short_name)
        self.assertEquals(self.election, election)
        
    def test_add_voters_file(self):
        pass

    def test_check_issues_before_freeze(self):
        # should be two issues: no trustees, and no questions
        issues = self.election.issues_before_freeze
        self.assertEquals(len(issues), 2)

        self.setup_questions()

        # should be one issue: no trustees
        issues = self.election.issues_before_freeze
        self.assertEquals(len(issues), 1)

        self.election.questions = None

        self.setup_trustee()

        # should be one issue: no trustees
        issues = self.election.issues_before_freeze
        self.assertEquals(len(issues), 1)
        
        self.setup_questions()

        issues = self.election.issues_before_freeze
        self.assertEquals(len(issues), 0)
        
    def test_helios_trustee(self):
        self.election.generate_trustee(ELGAMAL_PARAMS)

        self.assertTrue(self.election.has_helios_trustee())

        trustee = self.election.get_helios_trustee()        
        self.assertNotEquals(trustee, None)

    def test_log(self):
        LOGS = ["testing 1", "testing 2", "testing 3"]

        for l in LOGS:
            self.election.append_log(l)

        pulled_logs = [l.log for l in self.election.get_log().all()]
        pulled_logs.reverse()

        self.assertEquals(LOGS,pulled_logs)

    def test_eligibility(self):
        self.election.eligibility = [{'auth_system': self.user.user_type}]

        # without openreg, this should be false
        self.assertFalse(self.election.user_eligible_p(self.user))
        
        self.election.openreg = True

        # without openreg, and now true
        self.assertTrue(self.election.user_eligible_p(self.user))

    def test_freeze(self):
        # freezing without trustees and questions, no good
        def try_freeze():
            self.election.freeze()
        self.assertRaises(Exception, try_freeze)
        
        self.setup_questions()
        self.setup_trustee()

        # this time it should work
        try_freeze()
        
        # make sure it logged something
        self.assertTrue(len(self.election.get_log().all()) > 0)

    def test_archive(self):
        self.election.archived_at = datetime.datetime.utcnow()
        self.assertTrue(self.election.is_archived)

        self.election.archived_at = None
        self.assertFalse(self.election.is_archived)

    def test_voter_registration(self):
        # before adding a voter
        voters = models.Voter.get_by_election(self.election)
        self.assertTrue(len(voters) == 0)

        # make sure no voter yet
        voter = models.Voter.get_by_election_and_user(self.election, self.user)
        self.assertTrue(voter == None)

        # make sure no voter at all across all elections
        voters = models.Voter.get_by_user(self.user)
        self.assertTrue(len(voters) == 0)

        # register the voter
        voter = models.Voter.register_user_in_election(self.user, self.election)
        
        # make sure voter is there now
        voter_2 = models.Voter.get_by_election_and_user(self.election, self.user)

        self.assertFalse(voter == None)
        self.assertFalse(voter_2 == None)
        self.assertEquals(voter, voter_2)

        # make sure voter is there in this call too
        voters = models.Voter.get_by_user(self.user)
        self.assertTrue(len(voters) == 1)
        self.assertEquals(voter, voters[0])

        voter_2 = models.Voter.get_by_election_and_uuid(self.election, voter.uuid)
        self.assertEquals(voter, voter_2)

        self.assertEquals(voter.user, self.user)


class VoterModelTests(TestCase):
    fixtures = ['users.json', 'election.json']

    def setUp(self):
        self.election = models.Election.objects.get(short_name='test')

    def test_create_password_voter(self):
        v = models.Voter(uuid = uuid.uuid1(), election = self.election, voter_login_id = 'voter_test_1', voter_name = 'Voter Test 1')
        v.generate_password()

        v.save()
        
        # password has been generated!
        self.assertFalse(v.voter_password == None)

        # can't generate passwords twice
        self.assertRaises(Exception, lambda: v.generate_password())
        
