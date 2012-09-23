# Phoebus elections tests

import uuid
import tempfile
import os
import json
import random
import pprint
import tempfile

import django_webtest

from django.conf import settings

from auth import models as auth_models
from helios import models
from helios.crypto import elgamal
from helios.crypto.algs import *
from helios.crypto import electionalgs
from helios.views import ELGAMAL_PARAMS
from helios import utils, datatypes
from phoebus import phoebus as ph

class WebTest(django_webtest.WebTest):
    """
    Helper TestCase class.
    """
    def assertRedirects(self, response, url):
        """
        reimplement this in case it's a WebOp response
        and it seems to be screwing up in a few places too
        thus the localhost exception
        """
        if hasattr(response, 'location'):
            assert url in response.location
        else:
            assert url in response._headers['location'][1]
        self.assertEqual(response.status_code, 302)


    def assertContains(self, response, text):
        if hasattr(response, 'status_code'):
            assert response.status_code == 200
        else:
            assert response.status_int == 200

        if hasattr(response, "testbody"):
            assert text in response.testbody, "missing text %s" % text
        else:
            if hasattr(response, "body"):
                assert text in response.body, "missing text %s" % text
            else:
                assert text in response.content, "missing text %s" % text


class PhoebusElectionTests(WebTest):

    CANDIDATES = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6']
    VOTERS = 3

    def setUp(self):
        settings.AUTH_ENABLED_AUTH_SYSTEMS = ['password']

        auth_models.User.objects.create(user_id="admin", user_type="password",
                info={'password':'1234', 'name': 'Admin'}, name="Admin")

        self.admin = auth_models.User.objects.get(user_id="admin")
        super(PhoebusElectionTests, self).setUp()

    def _create_election(self, candidates=CANDIDATES):
        election = models.Election()
        election.short_name = 'test-election'
        election.name = 'Test election'
        election.description = 'Test election description'
        election.election_type = 'election'
        election.workflow_type = 'mixnet'
        election.uuid = str(uuid.uuid1())
        election.cast_url = '/' + election.uuid + '/cast/'
        election.admin = self.admin

        # election is private and not open for registration, administrator
        # will set the list of voters eligible to vote, which will be anonymous
        # by setting use_voter_aliases to True.
        election.openreg = False
        election.private_p = True
        election.use_voter_aliases = True

        election.save()
        return election

    def _add_custom_trustee(self, election, count=1):
        keypair = ELGAMAL_PARAMS.generate_keypair()
        name = "trustee"
        email = "trustee@%s" % election.uuid
        trustee = models.Trustee(uuid = str(uuid.uuid1()), election=election,
                                 name=name, email=email)
        trustee.save()

        response = self.client.post("/helios/elections/%s/trustees/%s/upload-pk" %
                (election.uuid, trustee.uuid), {'public_key_json': '{}'})
        self.assertEqual(response.status_code, 403)

        login = self.client.get("/helios/t/%s/%s/%s" %
                (election.short_name, trustee.email, trustee.secret))

        pk = keypair.pk
        pk_data = {'public_key': {'y': pk.y, 'p': pk.p, 'q': pk.q, 'g': pk.g}}
        proof = keypair.sk.prove_sk(DLog_challenge_generator)

        pk_data['pok'] = {'challenge': proof.challenge, 'commitment': proof.commitment,
                          'response': proof.response}
        response = self.client.post("/helios/elections/%s/trustees/%s/upload-pk" %
                (election.uuid, trustee.uuid), {'public_key_json':
                                                json.dumps(pk_data)})
        self._clear_login()
        return keypair.sk, trustee.email, trustee.secret, trustee.uuid

    def _upload_decryption_proofs(self, election, sk, email, secret, uuid):
        data = {'decryption_factors': [[]], 'decryption_proofs': [[]]}
        proofs_append = data['decryption_proofs'][0].append
        factors_append = data['decryption_factors'][0].append

        for cipher in election.encrypted_tally.tally[0]:
            factor, proof = sk.decryption_factor_and_proof(cipher)
            factors_append(factor)
            proof = {'challenge': proof.challenge,
                     'commitment': proof.commitment,
                     'response': proof.response}
            proofs_append(proof)


        response = self.client.post("/helios/elections/%s/trustees/%s/upload-decryption" %
                (election.uuid, uuid), data)

        self.assertEqual(response.status_code, 302)
        login = self.client.get("/helios/t/%s/%s/%s" %
                (election.short_name, email, secret))

        response = self.client.post("/helios/elections/%s/trustees/%s/upload-decryption" %
                                    (election.uuid, uuid), {'factors_and_proofs': json.dumps(data)})

        return data

    def _create_election_mixnets(self, election, count=1):
        for i in range(count):
            election.generate_helios_mixnet({"name":"helios mixnet %d" % i})

        return election.mixnets.all()

    def _create_election_questions(self, election):
        questions = []
        positions = len(self.CANDIDATES)
        for question_num in range(1):
            question = {}
            question['answer_urls'] = [None for x in range(positions)]
            question['choice_type'] = 'stv'
            question['question'] = 'Position %d choice' % question_num
            question['answers'] = self.CANDIDATES
            question['result_type'] = 'absolute'
            question['tally_type'] = 'stv'
            questions.append(question)

        election.questions = questions
        election.save()

    def _setup_login(self, user):
        # a bogus call to set up the session
        if type(self.client.session) == dict:
            self.client.get("/")

        # set up the session
        session = self.client.session
        session['user'] = {'type': user.user_type, 'user_id': user.user_id}
        session.save()

        # set up the app, too
        self.app.cookies['sessionid'] = self.client.cookies.get('sessionid').value

    def _setup_voter_login(self, voter):
        try:
            self._clear_login()
        except:
            pass

        # a bogus call to set up the session
        if type(self.client.session) == dict:
            self.client.get("/")

        # set up the session
        session = self.client.session
        session['CURRENT_VOTER'] = voter
        session.save()

        # set up the app, too
        self.app.cookies['sessionid'] = self.client.cookies.get('sessionid').value

    def _clear_login(self):
        session = self.client.session
        try:
            del session['user']
        except:
            pass

        try:
            del session['helios_trustee_uuid']
        except:
            pass

        try:
            del session['CURRENT_VOTER']
        except:
            pass

        session.save()

    def _upload_voters(self, election, voters_num=VOTERS):
        self._setup_login(self.admin)
        voters_file = os.fdopen(tempfile.mkstemp('phoebus-voters.csv')[0], 'r+w')

        # initialize csv contents for voters file
        contents = u""
        for v in range(self.VOTERS):
            contents += u"voter%d,voter%s@phoebus.grnet.gr,Voter%d Name\n" % (v,v,v)

        voters_file.write(contents)
        voters_file.seek(0)

        response = self.client.post("/helios/elections/%s/voters/upload" %
                election.uuid, {'voters_file': voters_file})

        # now we confirm the upload
        response = self.client.post("/helios/elections/%s/voters/upload" %
                election.uuid, {'confirm_p': "1"})
        self._clear_login()

        return models.Voter.objects.filter(election=election)

    def _freeze_election(self, election):
        self._setup_login(self.admin)
        response = self.client.post("/helios/elections/%s/freeze" % election.uuid, {
                "csrf_token" : self.client.session['csrf_token']})
        self._clear_login()

    def _cast_vote(self, election, voter, answers):
        answers = [answers]
        self._setup_voter_login(voter)
        response = self.app.post("/helios/elections/%s/encrypt-ballot" %
                election.uuid, {
                'answers_json': utils.to_json(answers)})
        self.assertContains(response, "answers")

        # parse it as an encrypted vote with randomness, and make sure randomness is there
        the_ballot = utils.from_json(response.testbody)
        assert the_ballot['answers'][0].has_key('randomness'), "no randomness"

        # parse it as an encrypted vote, and re-serialize it
        ballot = datatypes.LDObject.fromDict(utils.from_json(response.testbody),
                'phoebus/EncryptedVote')
        encrypted_vote = ballot.serialize()
        response = self.app.post("/helios/elections/%s/cast" % election.uuid, {
                'encrypted_vote': encrypted_vote})
        response = self.app.get("/helios/elections/%s/cast_confirm" % election.uuid)
        response.form.submit()
        response = self.app.get("/helios/elections/%s/cast_done" % election.uuid)


    def _compute_tally(self, election):
        # log back in as administrator
        self._setup_login(self.admin)
        # encrypted tally
        response = self.client.post("/helios/elections/%s/compute_tally" %
                election.uuid, {
                "csrf_token" : self.client.session['csrf_token']
                })
        self._clear_login()

    def _decrypt_tally(self, election):
        self._setup_login(self.admin)
        # combine decryptions
        response = self.client.post("/helios/elections/%s/combine_decryptions" %
                election.uuid, {
                "csrf_token" : self.client.session['csrf_token'],
                })
        self._clear_login()


    def _get_result(self, election):
        self._setup_login(self.admin)
        # check that tally matches
        response = self.client.get("/helios/elections/%s/result" % election.uuid)
        self._clear_login()
        return response.content

    def _get_election(self, election):
        return models.Election.objects.get(pk=election.pk)

    def _get_random_answer(self, candidates, answer=None):
        candidates = list(range(len(candidates)))
        choice = candidates[:random.choice(candidates)]
        random.shuffle(choice)

        if answer:
            choice = answer
        return ph.to_relative_answers(choice, len(candidates)), choice

    def _cast_audited_votes(self, election, nr):
        response = self.client.post("/helios/elections/%s/post-audited-ballot" %
                                   election.uuid, {})
        self.assertEqual(response.status_code, 302)

        voter = random.choice(list(election.voter_set.all()))
        rel, absolute = self._get_random_answer(self.CANDIDATES)
        election = self._get_election(election)
        audited_ballot = \
            electionalgs.EncryptedVote.fromElectionAndAnswers(election, [rel]).toJSONDict()
        self._setup_voter_login(voter)

        data = {'audited_ballot': json.dumps(audited_ballot)}
        response = self.client.post("/helios/elections/%s/post-audited-ballot" %
                                   election.uuid, data)

        self.assertEqual(response.status_code, 200)
        self._clear_login()

    def test_complete_election(self):
        # ballot preparation
        self.VOTERS = 3

        # ADMIN: Creates an election from admin election creation form.
        #        At a second step he sets the election questions.
        #        For STV we support only one question for each election.
        #        This may change by removing hardcoded [0]'s.
        election = self._create_election()
        self._create_election_questions(election)
        self.assertEqual(models.Election.objects.count(), 1)

        # ADMIN: At this step helios has already added the "Helios Trustee" to
        #        the election, lets a custom one. Administrator visits the
        #        election trustees page and add a trustee providing name,email
        #        of the trustee. _add_custom_trustee also mimics trustee visit
        #        to key creation page, by uploading a custom secret key.
        #        We keep sk, email, secret, uuid so that we
        #        may access the trustee page later to upload partial decription
        #        factors.
        # TODO: ADMIN: test send email to trustee (admin may notify trustee with
        #              the url needed for trustee to generate/upload her secret key.
        self.assertEqual(election.trustee_set.count(), 1)
        sk, email, secret, tuuid = self._add_custom_trustee(election)
        self.assertEqual(election.trustee_set.count(), 2)

        # This is done internally, no urls for mixnet avaiable yet in order
        # to make functional tests
        election = self._get_election(election)
        self._create_election_mixnets(election, 2)
        self.assertEqual(election.get_next_mixnet().mix_order, 0)

        # ADMIN: uploads voters file, election users get created
        self._upload_voters(election)
        election = self._get_election(election)
        self.assertEqual(election.voter_set.count(), self.VOTERS)

        # ADMIN: Freezes the election
        self._freeze_election(election)

        # USER: expert voter enters the voting booth and casts some audited
        #       votes.
        self._cast_audited_votes(election, 3)


        # USERS: Other voters: 1) May cast vote, 2) May not cast vote
        STORED_VOTES = [] # keep choices
        index = 0
        skipped_votes = 0
        for voter in models.Voter.objects.filter(election=election):
            if random.choice([1,2,3,4,5,6,7]) > 5:
                skipped_votes += 1
                continue

            relative_choice, absolute_choice = self._get_random_answer(self.CANDIDATES)
            STORED_VOTES.append(absolute_choice)
            self._cast_vote(election, voter, relative_choice)

        VOTES_CASTED = self.VOTES - skipped_votes

        # ADMIN: Computes tally (that also closes the election)
        self._compute_tally(election)
        election = self._get_election(election)
        # no mixnet in error state
        self.assertEqual(election.error_mixnet, None)
        # all mixnets finished
        self.assertEqual(self._get_election(election).mixing_finished, True)
        # election now have an encrypted tally
        self.assertEqual(bool(election.encrypted_tally), True)
        self.assertEqual(len(election.encrypted_tally.tally[0]), VOTES_CASTED)
        # test that mixed votes exist in
        for mixnet in election.mixnets.all():
            self.assertEqual(mixnet.status, 'finished')
            self.assertEqual(len(mixnet.mixed_answers), VOTES_CASTED)

        # eleciton not ready for decryption yet, custom trustees decryption
        # factors not uploaded yet.
        self.assertEqual(election.ready_for_decryption_combination(), False)

        # TRUSTEE: Uploads decryption factors from her browser.
        self._upload_decryption_proofs(election, sk, email, secret, tuuid)
        self.assertTrue(election.trustee_set.all()[0].decryption_factors)
        self.assertTrue(election.trustee_set.all()[1].decryption_factors)
        self.assertEqual(election.ready_for_decryption_combination(), True)

        # ADMIN: Admin requests helios to do the decryption.
        self._decrypt_tally(election)
        election = self._get_election(election)

        # Result exists in results page
        result = self._get_result(election)

        print list(election.result_choices)
        print STORED_VOTES

    def test_phoebus_encoding(self):
        from phoebus import phoebus as ph

        sk = ph._default_secret_key
        pk = ph._default_public_key

        e = ph.Election(public_key=pk, candidates=range(6))
        b = ph.Ballot(election=e, answers=[1, 3, 3, 0, 1])
        b.encrypt()

        eb = b.encrypted_ballot
        bd = ph.Ballot.from_dict({'encrypted_ballot':{
            'a': eb['a'], 'b': eb['b']},
            'public_key': pk, 'nr_candidates': 6, 'max_choices': 6})
        bd.decrypt(sk)

        for i in range(10):
            print ph.Ballot.mk_random(e)

        choice = [1,3,3,1,2,1]
        self.assertEqual(ph.gamma_decode(ph.gamma_encode([1,3,3,1,2,1], 6), 6),
                         choice)

    def test_mixnet_to_json(self):
        import copy

        sk = ph._default_secret_key
        pk = ph._default_public_key

        e = ph.Election(public_key=pk, candidates=self.CANDIDATES)
        e.cast_random_votes(2)
        mixed, proof = e.mix_ballots()
        import json
        jsondata = json.dumps(proof.to_dict())

        from phoebus.mixnet.ShufflingProof import ShufflingProof

        emixed = ph.Election(public_key=pk,
                             encrypted_ballots=copy.deepcopy(mixed),
                             candidates=self.CANDIDATES)

        jsondata = json.loads(jsondata)
        mixpk, nbits = ph.mixnet_pk(pk)
        newproof = ShufflingProof.from_dict(jsondata, mixpk, nbits)
        print newproof.verify(e.ballots_as_cipher_collection(),
                        emixed.ballots_as_cipher_collection())
