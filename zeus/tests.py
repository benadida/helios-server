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
import os
import zipfile
import cStringIO as StringIO
import pprint

from random import choice
from datetime import timedelta

from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.hashers import make_password

from helios.crypto.elgamal import *
from helios.crypto import algs
from helios.models import *
from helios import datatypes
from helios import tasks

from zeus.helios_election import *
from zeus.models import *
from zeus.core import *

from heliosauth.models import User

import datetime
import logging


TRUSTEES_COUNT = int(os.environ.get('ZEUS_TRUSTEES_COUNT', 2))
VOTERS_COUNT = int(os.environ.get('ZEUS_VOTERS_COUNT', 50))
VOTES_COUNT = int(os.environ.get('ZEUS_VOTES_COUNT', 2))
MIXNETS_COUNT = int(os.environ.get('ZEUS_MIXNETS_COUNT', 1))
REMOTE_MIXES_COUNT = int(os.environ.get('ZEUS_REMOTE_MIXNETS_COUNT', 2))
CAST_AUDITS = False
CAST_WITH_AUDIT_SECRET = False
DO_REMOTE_MIXES = True


def random_string(length=5, prefix="", vary=False):
    if not vary:
        rand = "".join([random.choice(string.ascii_uppercase + \
                                  string.ascii_lowercase) for x in \
                                  range(length)]).title()
    else:
        rand = "".join([random.choice(string.ascii_uppercase + \
                                  string.ascii_lowercase) for x in \
                                  range(choice(range(1, length)))]).title()
    if prefix:
        rand = "%s %s" % (prefix, rand)
    return rand


def random_sentence(words=10, prefix=""):
    return prefix + " ".join([random_string(random.choice(range(5,15))) for \
                              x in range(words)])


class FunctionalZeusTest(TestCase):

    def _random_questions(self, qcount=None, ccount=None):
        post_data = {}
        if not qcount:
            qcount = choice(range(1, 10))

        for q in range(qcount):
            if not ccount:
                choice_count = choice(range(1, 10))
            else:
                choice_count = ccount

            post_data['form-%d-question' % q] = "Question %d %s" % (q,
                                                            random_string(40))
            post_data['form-%d-choice_type' % q] = "choice"
            post_data['form-%d-min_answers' % q] = \
                    minchoice = str(choice(range(1, choice_count+1)))
            post_data['form-%d-max_answers' % q] = \
                    maxchoice = str(choice(range(int(minchoice), choice_count+1)))
            post_data['form-%d-ORDER' % q] = q

            for a in range(choice_count):
                post_data['form-%d-answer_%d' % (q, a)] = \
                        random_string(20, "Choice ", True)

        post_data['form-TOTAL_FORMS'] = qcount
        post_data['form-INITIAL_FORMS'] = 1
        post_data['form-MAX_NUM_FORMS'] = ""
        return post_data

    def _random_election_data(self, custom_data={}):

        trustees = "\n".join(",".join([random_sentence(2, u"Έφορος "),
                                       "eforos%d@trustee.com" % x]) for x in range(TRUSTEES_COUNT))
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
            'election_type': 'election_parties',
            'eligibles_count': 6,
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
        r = client.post('/auth/password/login',
                        {'username': user, 'password':pwd}, follow=True)
        self.assertContains(r, u"Έχετε συνδεθεί ως διαχειριστής")
        return client

    def election(self, uuid):
        return Election.objects.get(uuid=uuid)

    def get_client(self):
        return Client()

    def setUp(self):
        institution = Institution.objects.create(name="inst1")
        User.objects.create(user_type="password", user_id="admin",
                            info={"password": make_password("admin")},
                            admin_p=True, ecounting_account=False,
                            institution=institution)
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

        q_data = self._random_questions()
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

        # available answers
        selection = list(range(len(election.questions[0]['answers'])))

        random.shuffle(selection)
        selection = selection[:choice(range(len(selection)))]
        cands_size = len(election.questions[0]['answers'])
        rel_selection = to_relative_answers(selection, cands_size)
        encoded = gamma_encode(rel_selection, cands_size, cands_size)
        plaintext = algs.EGPlaintext(encoded, election.public_key)
        randomness = algs.Utils.random_mpz_lt(election.public_key.q)
        cipher = election.public_key.encrypt_with_r(plaintext,
                                                    randomness, True)

        modulus, generator, order = \
                election.zeus_election.do_get_cryptosystem()
        enc_proof = prove_encryption(modulus, generator, order, cipher.alpha,
                                     cipher.beta, randomness)

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
                votes.append({'voter': voter, 'encoded': encoded,
                              'audit': audit})

        print "VOTING"
        pprint.pprint(votes)
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
            mix = from_canonical(mix.content)
            new_mix = mix_ciphers(mix, nr_rounds=128, nr_parallel=4,
                                  teller=Teller())
            mixer.post(mix_url, data=to_canonical(new_mix),
                       content_type="application/binary")

            self.assertEqual(election.mixnets.count(), count+1)

    def exclude_voter(self, voter_obj, election, client):
        excluded = voter_obj
        # admin cannot delete a voter who already cast a vote
        r = client.get('/helios/elections/%s/voters/%s/delete' % (election.uuid,
                                                                  excluded.uuid))
        # but he may exclude him
        r = client.post('/helios/elections/%s/voters/%s/exclude' % (election.uuid,
                                                                  excluded.uuid),
                        {'reason':'spammer','confirm':1})
        self.assertEqual(r.status_code, 302)
        voter = Voter.objects.get(uuid=excluded.uuid)
        self.assertTrue(voter.excluded_at)
        self.assertEqual(voter.exclude_reason, u'spammer')
        r = client.post('/helios/elections/%s/voters/%s/exclude' % (election.uuid,
                                                                  excluded.uuid),
                        {'reason':'spammer','confirm':1})
        self.assertEqual(r.status_code, 403)
        return excluded

    def assert_anonymous_cannot_visit(self, election):
        c = self.get_client()
        r = c.get('/helios/elections/%s/view' % election.uuid, follow=True)
        self.assertEqual(r.status_code, 403)

    def assert_voter_cannot_vote(self, election, voter=None):
        v = voter or election.voter_set.filter()[choice(range(election.voter_set.count()))]
        c = self.get_client()
        c.get(v.get_quick_login_url())
        c.get('/helios/elections/%s/view' % election.uuid)
        r = c.post('/helios/elections/%s/cast' % (election.uuid,),
                   {'csrf_token': c.session.get('csrf_token')})
        self.assertEqual(r.status_code, 403)

    def test_complete(self):
        admin1, election = self.create_random_election(settings.TEST_ADMINS[0])
        kps = self.prepare_trustees(election.uuid)
        self.freeze_election(admin1, election.uuid)

        election = Election.objects.get(uuid=election.uuid)
        election.voting_starts_at = datetime.datetime.now() + timedelta(hours=2)
        election.save()

        # voter cannot vote before voting_starts_at
        self.assert_voter_cannot_vote(election)
        self.assert_anonymous_cannot_visit(election)

        # set proper voting starts at date and do random cast
        election = Election.objects.get(uuid=election.uuid)
        election.voting_starts_at = datetime.datetime.now()
        election.save()
        votes = self.random_votes(election.uuid)

        election = Election.objects.get(uuid=election.uuid)
        election.voting_ends_at = datetime.datetime.now()
        election.save()

        # voter cannot vote before voting_starts_at
        self.assert_voter_cannot_vote(election)
        self.assert_anonymous_cannot_visit(election)

        excluded = choice(votes)
        self.exclude_voter(excluded['voter'], election, admin1)
        votes.remove(excluded)

        self.mix_election(admin1, election.uuid)
        # check that no mix is stored in jsonfiled, this coz its deprecated
        mixnets = Election.objects.get(uuid=election.uuid).mixnets.all()
        self.assertTrue(mixnets.filter(status='finished').count() > 0)
        for mix in mixnets:
            assert mix.mix == None
            assert mix.parts.count() > 0

        # voter cannot vote while mixing
        self.assert_voter_cannot_vote(election)
        self.assert_anonymous_cannot_visit(election)

        if election.mix_key:
            self.add_remote_mixes(election.uuid)
            self.finish_mixing(admin1, election.uuid)

        self.trustees_decrypt(kps)

        r = admin1.get('/helios/elections/%s/zeus-proofs.zip' % election.uuid)
        self.assertEqual(r.status_code, 200)
        self._extract_and_validate_zip_proofs(r.content)

        # voter cannot vote after election is finished
        self.assert_voter_cannot_vote(election)
        self.assert_anonymous_cannot_visit(election)

    def _extract_and_validate_zip_proofs(self, zip_data):
        z = zipfile.ZipFile(StringIO(zip_data))
        fname = z.infolist()[0].filename
        pth = '/tmp/zeus_testproofs'
        z.extract(fname, path=pth)
        contents = file(pth+'/'+fname).read()
        finished = from_canonical(contents)
        election = ZeusCoreElection.new_at_finished(finished, teller=Teller(),
                                                    nr_parallel=4)
        self.assertEqual(election.validate(), True)

