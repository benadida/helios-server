"""
Unit Tests for Helios
"""

import unittest, datetime, re

import models
import datatypes

from auth import models as auth_models
from views import ELGAMAL_PARAMS
import views
import utils

from django.db import IntegrityError, transaction

from django.test.client import Client
from django.test import TestCase

from django.core import mail
from django.core.files import File
from django.core.urlresolvers import reverse

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
        election = self.election

        FILE = "helios/fixtures/voter-file.csv"
        vf = models.VoterFile.objects.create(election = election, voter_file = File(open(FILE), "voter_file.css"))
        vf.process()

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
        v = models.Voter(uuid = str(uuid.uuid1()), election = self.election, voter_login_id = 'voter_test_1', voter_name = 'Voter Test 1', voter_email='foobar@acme.com')

        v.generate_password()

        v.save()
        
        # password has been generated!
        self.assertFalse(v.voter_password == None)

        # can't generate passwords twice
        self.assertRaises(Exception, lambda: v.generate_password())
        
        # check that you can get at the voter user structure
        self.assertEquals(v.user.user_id, v.voter_email)


class CastVoteModelTests(TestCase):
    fixtures = ['users.json', 'election.json']

    def setUp(self):
        self.election = models.Election.objects.get(short_name='test')
        self.user = auth_models.User.objects.get(user_id='ben@adida.net', user_type='google')

        # register the voter
        self.voter = models.Voter.register_user_in_election(self.user, self.election)

    def test_cast_vote(self):
        assert False

class DatatypeTests(TestCase):
    fixtures = ['election.json']

    def setUp(self):
        self.election = models.Election.objects.all()[0]
        self.election.generate_trustee(ELGAMAL_PARAMS)

    def test_instantiate(self):
        ld_obj = datatypes.LDObject.instantiate(self.election.get_helios_trustee(), '2011/01/Trustee')
        foo = ld_obj.serialize()

    def test_from_dict(self):
        ld_obj = datatypes.LDObject.fromDict({
                'y' : '1234',
                'p' : '23434',
                'g' : '2343243242',
                'q' : '2343242343434'}, type_hint = 'pkc/elgamal/PublicKey')
        
        import pdb; pdb.set_trace()
        
        

##
## Black box tests
##

class DataFormatBlackboxTests(object):
    def setUp(self):
        self.election = models.Election.objects.all()[0]

    def assertEqualsToFile(self, response, file_path):
        expected = open(file_path)
        self.assertEquals(response.content, expected.read())
        expected.close()

    def test_election(self):
        response = self.client.get("/helios/elections/%s" % self.election.uuid, follow=False)
        self.assertEqualsToFile(response, self.EXPECTED_ELECTION_FILE)

    def test_voters_list(self):
        response = self.client.get("/helios/elections/%s/voters/" % self.election.uuid, follow=False)
        self.assertEqualsToFile(response, self.EXPECTED_VOTERS_FILE)

    def test_trustees_list(self):
        response = self.client.get("/helios/elections/%s/trustees/" % self.election.uuid, follow=False)
        self.assertEqualsToFile(response, self.EXPECTED_TRUSTEES_FILE)

    def test_ballots_list(self):
        response = self.client.get("/helios/elections/%s/ballots/" % self.election.uuid, follow=False)
        self.assertEqualsToFile(response, self.EXPECTED_BALLOTS_FILE)

## now we have a set of fixtures and expected results for various formats
## note how TestCase is used as a "mixin" here, so that the generic DataFormatBlackboxTests
## does not register as a set of test cases to run, but each concrete data format does.

class LegacyElectionBlackboxTests(DataFormatBlackboxTests, TestCase):
    fixtures = ['legacy-data.json']
    EXPECTED_ELECTION_FILE = 'helios/fixtures/legacy-election-expected.json'
    EXPECTED_VOTERS_FILE = 'helios/fixtures/legacy-election-voters-expected.json'
    EXPECTED_TRUSTEES_FILE = 'helios/fixtures/legacy-trustees-expected.json'
    EXPECTED_BALLOTS_FILE = 'helios/fixtures/legacy-ballots-expected.json'

class V3_1_ElectionBlackboxTests(DataFormatBlackboxTests, TestCase):
    fixtures = ['v3.1-data.json']
    EXPECTED_ELECTION_FILE = 'helios/fixtures/v3.1-election-expected.json'
    EXPECTED_VOTERS_FILE = 'helios/fixtures/v3.1-election-voters-expected.json'
    EXPECTED_TRUSTEES_FILE = 'helios/fixtures/v3.1-trustees-expected.json'
    EXPECTED_BALLOTS_FILE = 'helios/fixtures/v3.1-ballots-expected.json'

##
## overall operation of the system
##

class ElectionBlackboxTests(TestCase):
    fixtures = ['users.json', 'election.json']

    def setUp(self):
        self.election = models.Election.objects.all()[0]
        self.user = auth_models.User.objects.get(user_id='ben@adida.net', user_type='google')

    def test_get_election_shortcut(self):
        response = self.client.get("/helios/e/%s" % self.election.short_name, follow=True)
        self.assertContains(response, self.election.description)
        
    def test_get_election_raw(self):
        response = self.client.get("/helios/elections/%s" % self.election.uuid, follow=False)
        self.assertEquals(response.content, self.election.toJSON())
    
    def test_get_election(self):
        response = self.client.get("/helios/elections/%s/view" % self.election.uuid, follow=False)
        self.assertContains(response, self.election.description)

    def test_get_election_questions(self):
        response = self.client.get("/helios/elections/%s/questions" % self.election.uuid, follow=False)
        for q in self.election.questions:
            self.assertContains(response, q['question'])
    
    def test_get_election_trustees(self):
        response = self.client.get("/helios/elections/%s/trustees" % self.election.uuid, follow=False)
        for t in self.election.trustee_set.all():
            self.assertContains(response, t.name)

    def test_get_election_voters(self):
        response = self.client.get("/helios/elections/%s/voters/list" % self.election.uuid, follow=False)
        # check total count of voters
        if self.election.num_voters == 0:
            self.assertContains(response, "no voters")
        else:
            self.assertContains(response, "(of %s)" % self.election.num_voters)

    def test_get_election_voters_raw(self):
        response = self.client.get("/helios/elections/%s/voters/" % self.election.uuid, follow=False)
        self.assertEquals(len(utils.from_json(response.content)), self.election.num_voters)
        
    def test_election_creation_not_logged_in(self):
        response = self.client.post("/helios/elections/new", {
                "short_name" : "test-complete",
                "name" : "Test Complete",
                "description" : "A complete election test",
                "election_type" : "referendum",
                "use_voter_aliases": "0",
                "use_advanced_audit_features": "1",
                "private_p" : "0"})

        self.assertRedirects(response, "/auth/?return_url=/helios/elections/new")
        
    def test_do_complete_election(self):
        # a bogus call to set up the session
        self.client.get("/")

        # set up the session
        session = self.client.session
        session['user'] = {'type': self.user.user_type, 'user_id': self.user.user_id}
        session.save()

        # create the election
        response = self.client.post("/helios/elections/new", {
                "short_name" : "test-complete",
                "name" : "Test Complete",
                "description" : "A complete election test",
                "election_type" : "referendum",
                "use_voter_aliases": "0",
                "use_advanced_audit_features": "1",
                "private_p" : "0"})

        # we are redirected to the election, let's extract the ID out of the URL
        election_id = re.search('/elections/([^/]+)/', str(response['Location'])).group(1)

        # add helios as trustee
        response = self.client.post("/helios/elections/%s/trustees/add-helios" % election_id)
        self.assertRedirects(response, "/helios/elections/%s/trustees/view" % election_id)

        # check that helios is indeed a trustee
        response = self.client.get("/helios/elections/%s/trustees/view" % election_id)
        self.assertContains(response, "Trustee #1")

        # add a few voters, via file upload
        FILE = "helios/fixtures/voter-file.csv"
        voters_file = open(FILE)
        response = self.client.post("/helios/elections/%s/voters/upload" % election_id, {'voters_file': voters_file})
        voters_file.close()
        self.assertContains(response, "first few rows of this file")

        # now we confirm the upload
        response = self.client.post("/helios/elections/%s/voters/upload" % election_id, {'confirm_p': "1"})
        self.assertRedirects(response, "/helios/elections/%s/voters/list" % election_id)

        # and we want to check that there are now voters
        response = self.client.get("/helios/elections/%s/voters/" % election_id)
        self.assertEquals(len(utils.from_json(response.content)), 4)
        
        # add questions
        response = self.client.post("/helios/elections/%s/save_questions" % election_id, {
                'questions_json': utils.to_json([{"answer_urls": [None,None], "answers": ["Alice", "Bob"], "choice_type": "approval", "max": 1, "min": 0, "question": "Who should be president?", "result_type": "absolute", "short_name": "Who should be president?", "tally_type": "homomorphic"}]),
                'csrf_token': self.client.session['csrf_token']})

        self.assertContains(response, "SUCCESS")
        
        # freeze election
        response = self.client.post("/helios/elections/%s/freeze" % election_id, {
                "csrf_token" : self.client.session['csrf_token']})
        self.assertRedirects(response, "/helios/elections/%s/view" % election_id)

        assert False
        # vote by preparing a ballot via the server-side encryption

        # cast the ballot

        # confirm it

        # encrypted tally

        # should trigger helios decryption automatically

        # combine decryptions

        # check that tally matches
