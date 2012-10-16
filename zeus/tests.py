"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

import uuid
import datetime
import copy

from random import choice

from django.test import TestCase

from helios.crypto.elgamal import *
from helios.crypto import algs
from helios.models import *
from helios import datatypes
from helios import tasks

from zeus.helios_election import *
from zeus.models import *
from zeus.core import get_random_selection, encode_selection, prove_encryption

TRUSTEES_COUNT = 5
VOTERS_COUNT = 950
VOTES_COUNT = 10
MIXNETS_COUNT = 2

#TRUSTEES_COUNT = 2
#VOTERS_COUNT = 5
#VOTES_COUNT = 2

#class TestZeusElection(TestCase):

    #def test_mk_random(self):
        #HeliosElection.mk_random(uuid="testuuid")

class TestHeliosElection(TestCase):

    UUID = "test"

    def test_zeus_helios_election(self):
        pass

    @property
    def election(self):
        return Election.objects.get(uuid=self.UUID)

    def test_election_workflow(self):
        institution = Institution(name="test institution")
        e = Election(name="election test", uuid=self.UUID)
        e.questions = [{'answers':[1,2,3,4,5], 'choice_type': 'stv', 'result_type':
                        'absolute', 'tally_type': 'stv'}]
        e.save()

        self.assertEqual(self.election.zeus_election.do_get_stage(), "CREATING")

        # generate election zeus trustee
        self.election.generate_trustee()
        trustee = self.election.get_helios_trustee()
        self.assertTrue(self.election.get_helios_trustee())
        self.assertTrue(self.election.get_helios_trustee().secret_key)
        self.assertTrue(self.election.get_helios_trustee().public_key)

        # no additional internal trustees allowed
        self.election.generate_trustee()
        self.assertEqual(trustee, self.election.get_helios_trustee())

        # generate user trustees
        trustees_keys = {}
        for i in range(TRUSTEES_COUNT):
            t1 = Trustee.objects.create(election=self.election, name="t%d" % i,
                                        email="t%d@test.com" % i)

        for t1 in self.election.trustee_set.filter(secret_key__isnull=True):
            t1_kp = ELGAMAL_PARAMS.generate_keypair()
            pk = algs.EGPublicKey.from_dict(dict(p=t1_kp.pk.p, q=t1_kp.pk.q, g=t1_kp.pk.g,
                                            y=t1_kp.pk.y))
            pok = t1_kp.sk.prove_sk(DLog_challenge_generator)
            self.election.add_trustee_pk(t1, pk, pok)
            trustees_keys[t1.pk] = ([t1_kp, pok])

        for pk in trustees_keys:
            self.election.reprove_trustee(self.election.trustee_set.get(pk=pk))

        self.assertEqual(self.election.trustee_set.count(), TRUSTEES_COUNT+1)

        for i in range(VOTERS_COUNT):
            voter_uuid = str(uuid.uuid4())
            voter_id = email = name = "voter%d@testvoter.com" % i
            voter = Voter(uuid= voter_uuid, user = None, voter_login_id = voter_id,
                          voter_name = name, voter_email = email, election = self.election)
            voter.init_audit_passwords()
            voter.generate_password()
            voter.save()

        self.election.zeus_election.validate_creating()

        e = self.election
        e.frozen_at = datetime.datetime.now()
        e.save()
        self.assertEqual(self.election.zeus_election.do_get_stage(), "VOTING")

        VOTES_CASTED = 0
        SELECTIONS = {}
        for voter in range(VOTERS_COUNT):
            cast = choice(range(10)) > 1
            cast_with_audit_pass = choice(range(10)) > 5
            if voter == 0:
                continue

            if not VOTES_CASTED and voter == VOTERS_COUNT-1:
                cast = True

            if not cast:
                continue

            cast_votes_count = choice(range(VOTES_COUNT)) + 1
            voter_obj = e.voter_set.get(election=e,
                              voter_email='voter%d@testvoter.com' % voter)

            print "VOTER", voter
            for voter_vote_index in range(cast_votes_count):
                audit_password = ""
                cast_audit = choice(range(5)) > 3

                selection = get_random_selection(len(e.questions[0]['answers']))
                encoded = encode_selection(selection)

                plaintext = algs.EGPlaintext(encoded, e.public_key)
                randomness = algs.Utils.random_mpz_lt(e.public_key.q)
                cipher = e.public_key.encrypt_with_r(plaintext, randomness, True)

                modulus, generator, order = e.zeus_election.do_get_cryptosystem()
                enc_proof = prove_encryption(modulus, generator, order, cipher.alpha,
                                             randomness)

                ballot = {
                    'election_hash': self.election.hash,
                    'election_uuid': self.election.uuid,
                    'answers': [{
                        'encryption_proof': enc_proof,
                        'choices':[{'alpha': cipher.alpha, 'beta': cipher.beta}]
                    }]
                }

                if cast_with_audit_pass:
                    audit_password = choice(voter_obj.get_audit_passwords())

                session_enc_vote = None
                enc_vote = datatypes.LDObject.fromDict(ballot,
                        type_hint='phoebus/EncryptedVote').wrapped_obj

                if cast_audit:
                    enc_vote.answers[0].answers = [selection]
                    enc_vote.answers[0].randomness = [randomness]
                    # mess with original audit password, to force auditing vote to be
                    # get cast
                    audit_password = choice(voter_obj.get_audit_passwords()) + \
                            str(choice(range(10)))
                    session_enc_vote = datatypes.LDObject.fromDict(ballot,
                        type_hint='phoebus/EncryptedVote').wrapped_obj

                    signature = self.election.cast_vote(voter_obj, session_enc_vote,
                                            audit_password)

                    enc_vote = enc_vote.ld_object.includeRandomness().wrapped_obj
                    signature = self.election.cast_vote(voter_obj, enc_vote,
                                            audit_password)
                    print "VOTER", voter, "CASTED AUDIT BALLOT", selection
                    continue

                if cast_audit and range(10) > 9:
                    continue

                self.election.cast_vote(voter_obj, enc_vote, audit_password)
                print "VOTER", voter, "CASTED BALLOT", selection
                SELECTIONS[voter_obj.uuid] = selection

        self.election.zeus_election.validate_voting()

        e = self.election
        e.workflow_type = 'mixnet'
        e.save()
        e.voting_ended_at = datetime.datetime.now()
        e.save()

        for i in range(MIXNETS_COUNT):
            e.generate_helios_mixnet()

        self.assertEqual(self.election.zeus_election.do_get_stage(), "MIXING")
        tasks.election_compute_tally(e.pk)
        self.assertEqual(self.election.encrypted_tally.num_tallied, len(SELECTIONS.values()))

        e = self.election
        for tpk, val in trustees_keys.iteritems():
            trustee = e.trustee_set.get(pk=tpk)
            sk = val[0].sk
            decryption_factors = [[]]
            decryption_proofs = [[]]
            for vote in e.encrypted_tally.tally[0]:
                  dec_factor, proof = sk.decryption_factor_and_proof(vote)
                  decryption_factors[0].append(dec_factor)
                  decryption_proofs[0].append(proof)
            e.add_trustee_factors(trustee, decryption_factors,
                                decryption_proofs)

        e = self.election
        self.assertTrue(self.election.result)

        self.election.zeus_election.validate_decrypting()
        self.assertEqual(e.zeus_election.do_get_stage(), 'FINISHED')

        results = e.pretty_result['selections']

        from helios.counter import Counter
        results = ["".join(map(str, r)) for r in results]
        selections = ["".join(map(str, r)) for r in SELECTIONS.values()]
        assert Counter(results) == Counter(selections)
