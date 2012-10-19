# -*- coding: utf-8 -*-
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
from zeus.core import get_random_selection, encode_selection, \
    prove_encryption, to_absolute_answers, gamma_encode, to_relative_answers

TRUSTEES_COUNT = 5
VOTERS_COUNT = 950
VOTES_COUNT = 10
MIXNETS_COUNT = 1

TRUSTEES_COUNT = 5
VOTERS_COUNT = 4
VOTES_COUNT = 12

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
        settings.DEBUG = True
        institution = Institution(name="test institution")
        e = Election(name="election test", uuid=self.UUID)
        e.short_name = "test"
        e.departments = [
          "Φιλοσοφική Σχολή",
          "Σχολή Θετικών Επιστημών",
          "Ανεξάρτητο Παιδαγωγικό Τμήμα Δημοτικής Εκπαίδευσης"
        ]
        candidates = [
            {
            'department': u'Φιλοσοφική Σχολή',
            'father_name': u'Γεώργιος',
            'name': u'Ιωάννης',
            'surname': u'Παναγιωτόπουλος'
            },
            {
            'department': u'Φιλοσοφική Σχολή',
            'father_name': u'Γεώργιος',
            'name': u'Κώνσταντίνος',
            'surname': u'Δημητρίου'
            },
            {
            'department': u'Σχολή Θετικών Επιστημών',
            'father_name': u'Γεώργιος',
            'name': u'Κώνσταντίνος',
            'surname': u'Αναστόπουλος'
            },
            {
            'department': u'Ανεξάρτητο Παιδαγωγικό Τμήμα Δημοτικής Εκπαίδευσης',
            'father_name': u'Γεώργιος',
            'name': u'Βαγγέλης',
            'surname': u'Παπαδημητρίου'
            },
            {
            'department': u'Ανεξάρτητο Παιδαγωγικό Τμήμα Δημοτικής Εκπαίδευσης',
            'father_name': u'Ιωάννης',
            'name': u'Κώνσταντίνος',
            'surname': u'Τσουκαλάς'
            },
        ]

        NUM_ANSWERS = choice(range(5, 15))
        cands = [dict(choice(candidates)) for i in range(NUM_ANSWERS)]
        for i, cand in enumerate(cands):
          cand['name'] += str(i)

        e.candidates = cands
        e.questions = [{'choice_type': 'stv', 'result_type':
                        'absolute', 'tally_type': 'stv'}]
        e.update_answers()
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
            voter = Voter(uuid= voter_uuid, user = None, voter_login_id =
                          voter_id,voter_surname=name,
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

                cands_size = len(e.questions[0]['answers'])
                vote_size = choice(range(cands_size))
                selection = []
                for s in range(vote_size):
                  vchoice = choice(range(cands_size))
                  if not vchoice in selection:
                    selection.append(vchoice)

                rel_selection = to_relative_answers(selection, cands_size)
                encoded = gamma_encode(rel_selection, cands_size, cands_size)

                print "ENCODED", encoded
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
                    print "VOTER", voter, "AUDIT BALLOT", selection
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

        results = e.pretty_result['abs_selections']

        from helios.counter import Counter
        results = [",".join(map(str, r)) for r in results]
        selections = [",".join(map(str, r)) for r in SELECTIONS.values()]

        assert Counter(results) == Counter(selections)


        # validate ecounting results
        ecounting_results = self.election.ecounting_dict()['ballots']
        assert Counter(results) == Counter(selections)

        for voter, selection in SELECTIONS.iteritems():
          vote = selection
          print 20*"*"
          if not len(vote):
            print "EMPTY VOTE"
          for i, v in enumerate(vote):
            if v == 0:
              continue
            cand = self.election.candidates[v-1]
            print i+1, cand['surname'], cand['name'], cand['father_name']
          print 20*"*"

        ecounting_ballots = [[int(s['candidateTmpId'])-1 for s in ballot['votes']] for \
                              ballot in self.election.ecounting_dict()['ballots']]

        ecounting_selections = [",".join(map(str, r)) for r in ecounting_ballots]
        assert Counter(results) == Counter(selections) == Counter(ecounting_selections)
        #print 20*"="
        print json.dumps(self.election.ecounting_dict(), ensure_ascii=0)
        #print 20*"="

