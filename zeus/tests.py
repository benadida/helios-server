# -*- coding: utf-8 -*-
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

import uuid
import datetime
import copy
import string
import json
import md5

from random import choice
from datetime import timedelta

from django.test import TestCase
from django.test.client import Client

from helios.crypto.elgamal import *
from helios.crypto import algs
from helios.models import *
from helios import datatypes
from helios import tasks

from zeus.helios_election import *
from zeus.models import *
from zeus.core import get_random_selection, encode_selection, \
    prove_encryption, to_absolute_answers, gamma_encode, to_relative_answers

TRUSTEES_COUNT = 3
VOTERS_COUNT = 50
VOTES_COUNT = 5
MIXNETS_COUNT = 1
REMOTE_MIXES_COUNT = 2
CAST_AUDITS = False
CAST_WITH_AUDIT_SECRET = False
DO_REMOTE_MIXES = True


def random_string(length=5, prefix=""):
    rand = "".join([random.choice(string.ascii_uppercase + \
                                  string.ascii_lowercase) for x in \
                                  range(length)]).title()
    if prefix:
        rand = "%s %s" % (prefix, rand)
    return rand


def random_sentence(words=10, prefix=""):
    return prefix + " ".join([random_string(random.choice(range(5,15))) for x in range(words)])


class FunctionalZeusTest(TestCase):

    def _random_questions(self, schools, count=15):
        post_data = {
            'candidates_lastname':[],
            'candidates_name':[],
            'candidates_fathers_name':[],
            'candidates_department':[]
        }

        for j in range(count):
            school = choice(schools)
            lastname, name, fathers_name = random_sentence(3).split(" ")
            post_data['candidates_lastname'].append(lastname)
            post_data['candidates_name'].append(name)
            post_data['candidates_fathers_name'].append(fathers_name)
            post_data['candidates_department'].append(school)

        return post_data

    def _random_election_data(self, custom_data={}):

        trustees = "\n".join(",".join([random_sentence(2, u"Έφορος "),
                                       "eforos%d@trustee.com" % x]) for x in range(TRUSTEES_COUNT))
        departments = "\n".join(random_sentence(2, u"Τμήμα ") for x in range(10))

        date1, date2 = datetime.datetime.now() + timedelta(hours=48), datetime.datetime.now() + timedelta(hours=56)
        data = {
            'institution': random_string(23),
            'name': random_string(40, "Εκλογή"),
            'voting_starts_at_0': date1.strftime('%Y-%m-%d'),
            'voting_starts_at_1': date1.strftime('%H'),
            'voting_ends_at_0': date2.strftime('%Y-%m-%d'),
            'voting_ends_at_1': date2.strftime('%H'),
            'trustees': trustees,
            'description': random_sentence(40),
            'departments': departments,
            'eligibles_count': 6,
            'has_department_limit': 1,
            'help_email': 'test@test.com',
            'help_phone': 'phone1, phone2, 6999999999',
        }
        if DO_REMOTE_MIXES:
            data['remote_mix'] = 1

        data.update(custom_data)
        return data

    def _get_random_voters_file(self, count=VOTERS_COUNT):
        fname = "/tmp/random_voters.csv"
        fp = file(fname, "w")
        for i in range(count):
            email = "voter%d@test.com" % i
            name, surname, father_name = random_sentence(3).split(" ")
            fp.write("%s,%s,%s,%s\n" % (email, name, surname, father_name))
        fp.close()
        return fname

    def prepare_trustees(self, uuid):
        election = Election.objects.get(uuid=uuid)
        pks = {}
        for t in election.trustee_set.filter(secret_key__isnull=True):
            login_url = t.get_login_url()
            client = self.get_client()
            client.get(login_url)
            #client.post('/helios/elections/%s/trustees/%s/upload-pk')

            t1_kp = ELGAMAL_PARAMS.generate_keypair()
            pk = algs.EGPublicKey.from_dict(dict(p=t1_kp.pk.p, q=t1_kp.pk.q, g=t1_kp.pk.g, y=t1_kp.pk.y))
            pok = t1_kp.sk.prove_sk(DLog_challenge_generator)

            post_data = {'public_key_json':json.dumps({'public_key': pk.toJSONDict(),
                                     'pok': {'challenge': pok.challenge,
                                             'commitment': pok.commitment,
                                             'response': pok.response}})}

            r = client.post('/helios/elections/%s/trustees/%s/upload-pk' % (uuid,
                                                                        t.uuid),
                       post_data)
            # TODO: post verify-public
            t = Trustee.objects.get(pk=t.pk)
            t.last_verified_key_at = datetime.datetime.now()
            t.save()
            pks[t.uuid] = t1_kp

        return pks

    def admin_client(self, user=settings.TEST_ADMINS[0][0],
                    pwd=settings.TEST_ADMINS[0][1]):
        client = self.get_client()
        r = client.get('/auth/logout', follow=True)
        self.assertEqual(r.status_code, 200)
        r = client.post('/auth/password/login', {'username': user,
                                                     'password':pwd},
                            follow=True)
        self.assertContains(r, u"Έχετε συνδεθεί ως διαχειριστής")
        return client

    def election(self, uuid):
        return Election.objects.get(uuid=uuid)

    def get_client(self):
        return Client()

    def setUp(self):
        self.admin = self.admin_client()
        self.trustee = self.get_client()
        self.voter = self.get_client()

    def create_random_election(self, admin):
        # create an election
        admin = self.admin_client(*admin)
        r = admin.get('/admin/')
        self.assertRedirects(r, '/helios/elections/new')

        el_data = self._random_election_data()
        r = admin.post('/helios/elections/new',
                            el_data)
        #print r.context['election_form'].errors['__all__']
        election = Election.objects.filter().order_by('-created_at')[0]
        uuid = election.uuid
        questions_url = '/helios/elections/%s/questions' % uuid
        self.assertRedirects(r, questions_url)

        q_data = self._random_questions(election.departments)
        r = admin.post(questions_url, q_data)
        voters_upload_url = '/helios/elections/%s/voters/upload' % uuid
        self.assertRedirects(r, voters_upload_url)

        data = file(self._get_random_voters_file())
        r = admin.post(voters_upload_url, {'voters_file': data})
        r = admin.post(voters_upload_url, {'confirm_p': 1})
        voters_view_url = '/helios/elections/%s/voters/list' % uuid
        self.assertRedirects(r, voters_view_url)
        self.assertTrue(election.voter_set.count() > 0)
        return admin, Election.objects.get(uuid=uuid)

    def random_vote(self, voter):
        client = self.get_client()
        election = voter.election
        selection = list(range(len(election.questions[0]['answers'])))
        random.shuffle(selection)
        selection = selection[:choice(range(len(selection)))]
        cands_size =  len(election.candidates)
        rel_selection = to_relative_answers(selection, cands_size)
        encoded = gamma_encode(rel_selection, cands_size, cands_size)
        plaintext = algs.EGPlaintext(encoded, election.public_key)
        randomness = algs.Utils.random_mpz_lt(election.public_key.q)
        cipher = election.public_key.encrypt_with_r(plaintext, randomness, True)

        modulus, generator, order = election.zeus_election.do_get_cryptosystem()
        enc_proof = prove_encryption(modulus, generator, order, cipher.alpha,
                                     randomness)

        client.get(voter.get_quick_login_url(), follow=True)
        cast_data = {}
        cast_data['csrf_token'] = client.session.get('csrf_token')

        ballot = {
            'election_hash': election.hash,
            'election_uuid': election.uuid,
            'answers': [{
                'encryption_proof': enc_proof,
                'choices':[{'alpha': cipher.alpha, 'beta': cipher.beta}]
            }]
        }

        audit = CAST_AUDITS and bool(choice(range(100)) > 80)

        use_audit_pass =  CAST_WITH_AUDIT_SECRET and bool(choice(range(100)) > 80)

        if use_audit_pass:
            pass

        enc_vote = datatypes.LDObject.fromDict(ballot,
                type_hint='phoebus/EncryptedVote').wrapped_obj

        cast_data['encrypted_vote'] = enc_vote.toJSON()
        client.post('/helios/elections/%s/cast' % election.uuid, cast_data)
        return voter, encoded, audit

    def random_votes(self, uuid):
        votes = []
        for voter in Election.objects.get(uuid=uuid).voter_set.all():
            if choice(range(10)) > 3:
                voter, encoded, audit = self.random_vote(voter)
                votes.append({'voter': voter, 'encoded': encoded, 'audit': audit})

        return votes

    def freeze_election(self, admin, uuid):
        r = admin.post('/helios/elections/%s/freeze' % uuid, {'csrf_token': admin.session.get('csrf_token')})

    def mix_election(self, admin, uuid):
        r = admin.post('/helios/elections/%s/compute_tally' % uuid, {'csrf_token': admin.session.get('csrf_token')})

    def finish_mixing(self, admin, uuid):
        r = admin.post('/helios/elections/%s/stop-mixing' % uuid, {'csrf_token': admin.session.get('csrf_token')})

    def trustees_decrypt(self, trustees):
        for trustee, kp in trustees.iteritems():
            t = Trustee.objects.get(uuid=trustee)
            client = self.get_client()
            client.get(t.get_login_url())

            sk = kp.sk
            decryption_factors = [[]]
            decryption_proofs = [[]]
            for vote in t.election.encrypted_tally.tally[0]:
                  dec_factor, proof = sk.decryption_factor_and_proof(vote)
                  decryption_factors[0].append(dec_factor)
                  decryption_proofs[0].append({
                      'commitment':proof.commitment,
                      'response': proof.response,
                      'challenge': proof.challenge
                  })

            data = {'decryption_factors': decryption_factors,
                          'decryption_proofs': decryption_proofs}

            r = client.post('/helios/elections/%s/trustees/%s/upload-decryption' % (t.election.uuid, t.uuid),
                        {'factors_and_proofs': json.dumps(data)})

    def add_remote_mixes(self, uuid, count=REMOTE_MIXES_COUNT):
        election = Election.objects.get(uuid=uuid)
        count = election.mixnets.count()
        for mix in range(count):
            mixer = self.get_client()
            mix_url = election.get_mix_url()
            mix = mixer.get(mix_url)
            mix = json.loads(mix.content)
            new_mix = mix_ciphers(mix, nr_rounds=128, nr_parallel=4)
            mixer.post(mix_url, data=json.dumps(new_mix),
                       content_type="application/json")

            self.assertEqual(election.mixnets.count(), count+1)

    def test_complete(self):
        admin1, election = self.create_random_election(settings.TEST_ADMINS[0])
        kps = self.prepare_trustees(election.uuid)
        self.freeze_election(admin1, election.uuid)

        election = Election.objects.get(uuid=election.uuid)
        election.voting_starts_at = datetime.datetime.now()
        election.save()
        votes = self.random_votes(election.uuid)

        election = Election.objects.get(uuid=election.uuid)
        election.voting_ends_at = datetime.datetime.now()
        election.save()

        # voter cannot vote after voting ends at
        v = election.voter_set.filter()[choice(range(election.voter_set.count()))]
        c = self.get_client()
        c.get(v.get_quick_login_url())
        c.get('/helios/elections/%s/view' % election.uuid)
        r = c.post('/helios/elections/%s/cast' % (election.uuid,),
                   {'csrf_token': c.session.get('csrf_token')})
        self.assertEqual(r.status_code, 403)

        self.mix_election(admin1, election.uuid)
        # check that no mix is stored in jsonfiled, this coz its deprecated
        mixnets = Election.objects.get(uuid=election.uuid).mixnets.all()
        self.assertTrue(mixnets.filter(status='finished').count() > 0)
        for mix in mixnets:
            assert mix.mix == None
            assert mix.parts.count() > 0

        if election.mix_key:
            self.add_remote_mixes(election.uuid)
            self.finish_mixing(admin1, election.uuid)

        self.trustees_decrypt(kps)

        self.assertEqual(Election.objects.get(uuid=election.uuid).ecounting_request_send,
                        None)
        admin1.post('/helios/elections/%s/post-ecounting' % election.uuid, {'csrf_token':
                                                            admin1.session.get('csrf_token')})
        self.assertTrue(Election.objects.get(uuid=election.uuid).ecounting_request_send,
                        None)
        election = Election.objects.get(uuid=election.uuid)
        vote_results = filter(lambda x:x is not False, map(lambda x:x['encoded'] if not x['audit'] else False,
                           votes))
        self.assertEqual(sorted(election.result[0]), sorted(vote_results))


class TestHeliosElection(TestCase):

    UUID = "test"

    def test_zeus_helios_election(self):
        pass

    @property
    def election(self):
        return Election.objects.get(uuid=self.UUID)

    def test_election_workflow(self):
        #settings.DEBUG = True
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
            voter_name = "Ψηφοφόρος %d" % i
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
                    enc_vote.answers[0].answer = [selection]
                    enc_vote.answers[0].randomness = [randomness]
                    # mess with original audit password, to force auditing vote to be
                    # get cast
                    audit_password = choice(voter_obj.get_audit_passwords()) + \
                            str(choice(range(10)))
                    session_enc_vote = datatypes.LDObject.fromDict(ballot,
                        type_hint='phoebus/EncryptedVote').wrapped_obj

                    signature = self.election.cast_vote(voter_obj, session_enc_vote,
                                            audit_password)
                    print "VOTER", voter, "AUDIT REQUEST", selection

                    enc_vote = enc_vote.ld_object.includeRandomness().wrapped_obj
                    if choice([0,1]) == 0:

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

        for a in AuditedBallot.objects.filter(is_request=False):
          assert a.vote.encrypted_answers[0].answer != None
          assert a.vote.encrypted_answers[0].randomness != None

        e = self.election
        e.workflow_type = 'mixnet'
        e.save()
        e.voting_ended_at = datetime.datetime.now()
        e.save()

        for i in range(MIXNETS_COUNT):
            e.generate_helios_mixnet()

        self.assertEqual(self.election.zeus_election.do_get_stage(), "MIXING")

        tasks.election_compute_tally(e.pk)
        tasks.validate_mixing(e.pk)

        self.assertEqual(self.election.bad_mixnet(), None)
        self.assertTrue(self.election.encrypted_tally)
        self.assertEqual(self.election.encrypted_tally.num_tallied, len(SELECTIONS.values()))

        e = self.election
        tasks.tally_helios_decrypt(e.pk)
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
        tasks.tally_decrypt(e.pk)
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

