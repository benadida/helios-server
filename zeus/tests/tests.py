import datetime
import json
from itertools import izip, chain
from random import shuffle, sample, randint
from datetime import timedelta


from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.test.client import Client


from zeus.core import to_relative_answers, gamma_encode, prove_encryption
from helios.views import ELGAMAL_PARAMS
from helios.crypto import algs
from helios.crypto.elgamal import *
from zeus.models.zeus_models import Institution
from heliosauth.models import User
from helios.models import *


class SetUpAdminAndClientMixin():

    def setUp(self):
        institution = Institution.objects.create(name="test_inst")
        self.admin = User.objects.create(user_type="password",
                                         user_id="test_admin",
                                         info={"password": make_password("test_admin")},
                                         admin_p=True,
                                         institution=institution)
        self.locations = {'home': '/',
                          'logout': '/auth/auth/logout',
                          'login':'/auth/auth/login',
                          'create': '/elections/new'}
        self.login_data = {'username': 'test_admin', 'password': 'test_admin'}
        self.c = Client()


# subclass order is significant
class TestUsersWithClient(SetUpAdminAndClientMixin, TestCase):

    def setUp(self):
        super(TestUsersWithClient, self).setUp()

    def test_user_on_login_page(self):
        r = self.c.get('/', follow=True)
        self.assertEqual(r.status_code, 200)

    def test_admin_login_with_creds(self):
        r = self.c.post(self.locations['login'], self.login_data, follow=True)
        self.assertEqual(r.status_code, 200)
        # user has no election so it redirects from /admin to /elections/new
        self.assertRedirects(r, self.locations['create'])

    def test_forbid_logged_admin_to_login(self):
        self.c.post(self.locations['login'], self.login_data)
        r = self.c.post(self.locations['login'], self.login_data)
        self.assertEqual(r.status_code, 403)

    def test_admin_login_wrong_creds(self):
        wrong_creds = {'username': 'wrong_admin', 'password': 'wrong_password'}
        r = self.c.post(self.locations['login'], wrong_creds)
        # if code is 200 user failed to login and wasn't redirected
        self.assertEqual(r.status_code, 200)

    def test_logged_admin_can_logout(self):
        self.c.post(self.locations['login'], self.login_data)
        r = self.c.get(self.locations['logout'], follow=True)
        self.assertRedirects(r, self.locations['home'])


class TestElectionBase(SetUpAdminAndClientMixin, TestCase):

    def setUp(self):
        super(TestElectionBase, self).setUp()
        self.local_verbose = True
        self.celebration =(
       " _________ ___  __\n"
       "|\   __  \|\  \|\  \\\n"
       "\ \  \ \  \ \  \/  /_\n"   
       " \ \  \ \  \ \   ___ \\\n"
       "  \ \  \_\  \ \  \\\ \ \\ \n"
       "   \ \_______\ \__\\\ \_\\\n"
       "    \|_______|\|__| \|_|\n")
                                           
        # set the voters number that will be produced for test
        self.voters_num = 2
        # set the trustees number that will be produced for the test
        trustees_num = 2 
        trustees = "\n".join(",".join(['testName%x testSurname%x' %(x,x),
                                       'test%x@mail.com' %x]) for x in range(0,trustees_num))
        # set the polls number that will be produced for the test
        self.polls_number = 2
        # set the number of max questions for simple election
        self.simple_election_max_questions_number = 3
        # set the number of max answers for each question of simple election
        self.simple_election_max_answers_number = 4 
        # set the number of max answers in score election
        self.score_election_max_answers = 13
        start_time = datetime.datetime.now()
        end_time = datetime.datetime.now() + timedelta(hours=2)
        date1, date2 = datetime.datetime.now() + timedelta(hours=48),datetime.datetime.now() + timedelta(hours=56)
        self.election_form = {
                              'trial': True,
                              'name': 'test_election',
                              'description': 'testing_election',
                              'trustees': trustees,
                              'voting_starts_at_0': date1.strftime('%Y-%m-%d'),
                              'voting_starts_at_1': date1.strftime('%H:%M'),
                              'voting_ends_at_0': date2.strftime('%Y-%m-%d'),
                              'voting_ends_at_1': date2.strftime('%H:%M'),
                              'help_email': 'test@test.com',
                              'help_phone': 6988888888,
                              'communication_language': 'el',
                              }

    def admin_can_submit_election_form(self):
        self.c.post(self.locations['login'], self.login_data)
        self.election_form['election_module'] = self.election_type 
        r = self.c.post(self.locations['create'], self.election_form, follow=True) 
        e = Election.objects.all()[0]
        self.e_uuid = e.uuid
        self.assertIsInstance(e, Election)
        if self.local_verbose:
            print 'Admin posted election form'

    def prepare_trustees(self,e_uuid):
        e = Election.objects.get(uuid=e_uuid)
        pks = {}
        for t in e.trustees.all():
            if not t.secret_key:
                login_url = t.get_login_url()
                self.c.get(self.locations['logout'])
                r = self.c.get(login_url)
                self.assertEqual(r.status_code, 302)
                t1_kp = ELGAMAL_PARAMS.generate_keypair()
                pk = algs.EGPublicKey.from_dict(dict(p=t1_kp.pk.p, 
                                                     q=t1_kp.pk.q,
                                                     g=t1_kp.pk.g,
                                                     y=t1_kp.pk.y))
                pok = t1_kp.sk.prove_sk(DLog_challenge_generator)
                post_data = {
                             'public_key_json':[json.dumps({'public_key': pk.toJSONDict(), 
                             'pok': {'challenge': pok.challenge,
                             'commitment': pok.commitment,
                             'response': pok.response}})]}

                r = self.c.post('/elections/%s/trustee/upload_pk' %
                               (e_uuid), post_data, follow=True)
                self.assertEqual(r.status_code, 200)
                t = Trustee.objects.get(pk=t.pk)
                t.last_verified_key_at = datetime.datetime.now()
                t.save()
                pks[t.uuid] = t1_kp
        if self.local_verbose:
            print 'Trustees are ready'
        return pks

    def freeze_election(self):
        e = Election.objects.get(uuid=self.e_uuid)
        self.c.get(self.locations['logout'])
        r = self.c.post(self.locations['login'], self.login_data)
        freeze_location = '/elections/%s/freeze' % self.e_uuid
        r = self.c.post(freeze_location, follow=True)
        e = Election.objects.get(uuid=self.e_uuid)
        if e.frozen_at:
            if self.local_verbose:
                print 'Election got frozen'
            return True

    def create_random_polls(self):
        self.c.get(self.locations['logout'])
        self.c.post(self.locations['login'], self.login_data)
        e = Election.objects.all()[0]
        # there shouldn't be any polls before we create them
        self.assertEqual(e.polls.all().count(), 0)
        location = '/elections/%s/polls/add' % self.e_uuid
        post_data = {'form-TOTAL_FORMS': self.polls_number,
                     'form-INITIAL_FORMS': 0,
                     'form-MAX_NUM_FORMS': 100
                    }
        for i in range(0, self.polls_number):
            post_data['form-%s-name'% i] = 'test_poll%s' % i

        self.c.post(location, post_data)
        e = Election.objects.all()[0]
        self.assertEqual(e.polls.all().count(), self.polls_number)
        if self.local_verbose:
            print 'Polls were created'
        self.p_uuids = [] 
        for poll in e.polls.all():
            self.p_uuids.append(poll.uuid)

    def submit_questions(self):
        post_data = self.create_questions()
        # post same questions to each poll - change later
        for p_uuid in self.p_uuids:
            questions_location = '/elections/%s/polls/%s/questions/manage' % \
                    (self.e_uuid, p_uuid)
            r = self.c.post(questions_location, post_data)
            p = Poll.objects.get(uuid=p_uuid)
            self.assertTrue(p.questions_count > 0)
        if self.local_verbose:
            print 'Questions were created'

    def get_random_voters_file(self):
        counter = 0
        voter_files = {}
        for p_uuid in self.p_uuids:
            fname = '/tmp/random_voters%s.csv' % counter
            voter_files[p_uuid] = fname
            fp = file(fname, 'w')
            for i in range(1,self.voters_num+1):
                voter = "%s,voter%s@mail.com,test_name%s,test_surname%s\n"%(i,i,i,i)
                fp.write(voter)
            fp.close()
            counter += 1
            #assert here
        if self.local_verbose:
            print 'Voters file created'
        return voter_files

    def submit_voters_file(self):
        voter_files = self.get_random_voters_file()
        for p_uuid in self.p_uuids:
            upload_voters_location = '/elections/%s/polls/%s/voters/upload' %(self.e_uuid, p_uuid)
            r = self.c.post(upload_voters_location, {'voters_file':file(voter_files[p_uuid])})
            r = self.c.post(upload_voters_location, {'confirm_p': 1})
        e = Election.objects.get(uuid=self.e_uuid)
        voters = e.voters.count()
        self.assertEqual(voters, self.voters_num*self.polls_number)
        if self.local_verbose:
            print 'Voters file submitted'

    def get_voters_urls(self):
        # return a dict with p_uuid as key and voters urls as a list for each poll
        voters_urls = {}
        for p_uuid in self.p_uuids:
            urls_for_this_poll = []
            p = Poll.objects.get(uuid=p_uuid)
            voters = p.voters.all()
            for v in voters:
                urls_for_this_poll.append(v.get_quick_login_url())
            voters_urls[p_uuid] = urls_for_this_poll
        if self.local_verbose:
            print 'Got login urls for voters'
        return voters_urls

    def voter_cannot_vote_before_freeze(self):
        voter_login_url = (Election.objects
            .get(uuid=self.e_uuid)
            .voters.all()[0]
            .get_quick_login_url())
        p_uuid = self.p_uuids[0]
        r = self.single_voter_cast_ballot(voter_login_url, p_uuid)
        self.assertEqual(r.status_code, 403)
        if self.local_verbose:
            print '...but was not allowed'

    def submit_vote_for_each_voter(self, voters_urls):
        for p_uuid in voters_urls:
            for voter_url in voters_urls[p_uuid]:
                self.single_voter_cast_ballot(voter_url, p_uuid)
        for p_uuid in self.p_uuids:
            p = Poll.objects.get(uuid=p_uuid)
            self.assertEqual(p.voters_cast_count(), self.voters_num)

    def single_voter_cast_ballot(self, voter_url, p_uuid):
        # make balot returns ballot_data and size
        data = self.make_ballot(p_uuid)
        r = self.encrypt_ballot_and_cast(data[0], data[1], voter_url, p_uuid)
        return r

    def make_ballot(self, p_uuid):
        raise Exception(NotImplemented)

    def encrypt_ballot_and_cast(self, selection, size, the_url, p_uuid):
        e = Election.objects.get(uuid=self.e_uuid)
        rel_selection = to_relative_answers(selection, size)
        encoded = gamma_encode(rel_selection, size, size)
        plaintext = algs.EGPlaintext(encoded, e.public_key)
        randomness = algs.Utils.random_mpz_lt(e.public_key.q)
        cipher = e.public_key.encrypt_with_r(plaintext, randomness, True)
        modulus, generator, order = e.zeus.do_get_cryptosystem()
        enc_proof = prove_encryption(modulus, generator, order, cipher.alpha,
                                     cipher.beta, randomness)
        r = self.c.get(the_url, follow=True)
        self.assertEqual(r.status_code, 200)
        cast_data = {}
        ##############
        ballot = {
                  'election_hash': 'foobar',
                  'election_uuid': e.uuid,
                  'answers': [{
                               'encryption_proof':enc_proof,
                               'choices':[{'alpha': cipher.alpha, 'beta': cipher.beta}]
                              }]
                 }
        ##############
        enc_vote = datatypes.LDObject.fromDict(ballot,
                type_hint='phoebus/EncryptedVote').wrapped_obj
        cast_data['encrypted_vote'] = enc_vote.toJSON()
        r = self.c.post('/elections/%s/polls/%s/cast'%(self.e_uuid, p_uuid), cast_data)
        if self.local_verbose:
            print 'Voter voted'
        return r

    def close_election(self):
        self.c.get(self.locations['logout'])
        r = self.c.post(self.locations['login'], self.login_data)
        self.c.post('/elections/%s/close'%self.e_uuid)
        e = Election.objects.get(uuid=self.e_uuid)
        self.assertTrue(e.feature_closed)
        if self.local_verbose:
            print 'Election is closed'

    def decrypt_with_trustees(self, pks):
        for trustee, kp in pks.iteritems():
            t = Trustee.objects.get(uuid=trustee)
            self.c.get(self.locations['logout'])
            self.c.get(t.get_login_url())

            sk = kp.sk
            for p_uuid in self.p_uuids:
                p = Poll.objects.get(uuid=p_uuid)
                decryption_factors = [[]]
                decryption_proofs = [[]]
                for vote in p.encrypted_tally.tally[0]:
                    dec_factor, proof = sk.decryption_factor_and_proof(vote)
                    decryption_factors[0].append(dec_factor)
                    decryption_proofs[0].append({
                        'commitment': proof.commitment,
                        'response': proof.response,
                        'challenge': proof.challenge,
                        })
                data = {'decryption_factors': decryption_factors,
                            'decryption_proofs': decryption_proofs}
                location = '/elections/%s/polls/%s/post-decryptions' % (self.e_uuid, p_uuid)
                post_data = {'factors_and_proofs': json.dumps(data)}
                r = self.c.post(location, post_data)
                self.assertEqual(r.status_code, 200)
                if self.local_verbose:
                    print 'Trustee decrypted poll'

    def check_results(self):
        # check if results exist
        for p_uuid in self.p_uuids:
            p = Poll.objects.get(uuid=p_uuid)
            self.assertTrue(len(p.result[0]) > 0)
            if self.local_verbose:
                print 'Results are generated for poll'

    def election_proccess(self):
        self.admin_can_submit_election_form()
        self.assertEqual(self.freeze_election(), None)
        pks = self.prepare_trustees(self.e_uuid)
        self.create_random_polls()
        self.submit_voters_file()
        self.submit_questions()
        self.voter_cannot_vote_before_freeze()
        e = Election.objects.get(uuid=self.e_uuid)
        self.assertEqual (e.election_issues_before_freeze, [])
        self.assertTrue(self.freeze_election())
        e = Election.objects.get(uuid=self.e_uuid)
        e.voting_starts_at = datetime.datetime.now()
        e.save()
        voters_urls = self.get_voters_urls() 
        self.submit_vote_for_each_voter(voters_urls)
        self.close_election()
        e = Election.objects.get(uuid=self.e_uuid)
        self.assertTrue(e.feature_mixing_finished)
        self.decrypt_with_trustees(pks)
        self.check_results()
        if self.local_verbose:
            print self.celebration

class TestSimpleElection(TestElectionBase):

    def setUp(self):
        super(TestSimpleElection, self).setUp()
        self.election_type = 'simple'
        if self.local_verbose:
            print '* Starting simple election *'

    def create_questions(self):
        max_nr_questions = self.simple_election_max_questions_number
        max_nr_answers = self.simple_election_max_answers_number
        nr_questions = randint(1, max_nr_questions)
        
        post_data = {'form-TOTAL_FORMS': nr_questions,
                     'form-INITIAL_FORMS': 1,
                     'form-MAX_NUM_FORMS': "",
                    }
        for num in range(0, nr_questions):
            nr_answers = randint(1, max_nr_answers)
            min_choices = randint(1, nr_answers)
            max_choices = randint(min_choices, nr_answers)
            extra_data = {}
            extra_data = {
                'form-%s-ORDER'%num: num,
                'form-%s-choice_type'%num: 'choice',
                'form-%s-question'%num: 'test_question_%s'%num,
                'form-%s-min_answers'%num: min_choices,
                'form-%s-max_answers'%num: max_choices,
                }
            for ans_num in range(0,nr_answers):
                extra_data['form-%s-answer_%s'%(num, ans_num)] = 'test answer %s' %ans_num
            post_data.update(extra_data) 
        return post_data

    def make_ballot(self, p_uuid):
        pass 

    def test_election_proccess(self):
        self.election_proccess()


class TestPartyElection(TestElectionBase):

    def setUp(self):
        super(TestPartyElection, self).setUp()
        self.election_type = 'parties'
        if self.local_verbose:
            print '* Starting party election *'

    def create_questions(self):

        post_data = {'form-TOTAL_FORMS': 2,
                     'form-INITIAL_FORMS': 1,
                     'form-MAX_NUM_FORMS': "",
                     'form-0-choice_type': 'choice',
                     'form-0-question': 'test_question',
                     'form-0-min_answers': 1,
                     'form-0-max_answers': 1,
                     'form-0-answer_0': 'test answer 0',
                     'form-0-answer_1': 'test answer 1',
                     'form-0-ORDER': 0,
                     'form-1-choice_type': 'choice',
                     'form-1-question': 'test_question1',
                     'form-1-min_answers': 1,
                     'form-1-max_answers': 1,
                     'form-1-answer_0': 'test answer 1-0',
                     'form-1-answer_1': 'test answer 1-1',
                     'form-1-ORDER': 1,
                     }
        return post_data
    
    def test_election_proccess(self):
        self.election_proccess()

# used for creating score elections ballot
def make_random_range_ballot(candidates_to_index, scores_to_index):

    candidate_indexes = candidates_to_index.values()
    score_indexes = scores_to_index.values()
    nr_scores = len(score_indexes)
    nr_candidates = len(candidate_indexes)
    max_nr_choices = min(nr_candidates, nr_scores)

    selected_score_indexes = \
        sample(score_indexes, randint(0, max_nr_choices))
    selected_score_indexes.sort()
    selected_candidate_indexes = sample(candidate_indexes,
                                 len(selected_score_indexes))
    shuffle(selected_candidate_indexes)
    ballot_choices = izip(selected_candidate_indexes, selected_score_indexes)
    ballot_choices = chain(*ballot_choices)
    ballot_choices = list(ballot_choices)
    max_ballot_choices = nr_scores + nr_candidates
    
    return ballot_choices, max_ballot_choices


class TestScoreElection(TestElectionBase):

    def setUp(self):
        super(TestScoreElection, self).setUp()
        self.election_type = 'score'
        if self.local_verbose:
            print '* Starting score election *'

    def create_questions(self):
        max_nr_answers = self.score_election_max_answers
        nr_answers = randint(1, max_nr_answers)
        available_scores = [x for x in range (1,10)]
        nr_scores_selection = randint(1,9)
        scores_list = sample(available_scores, nr_scores_selection)
        scores_list.sort()
        post_data = {'form-TOTAL_FORMS': 1,
                     'form-INITIAL_FORMS': 1,
                     'form-MAX_NUM_FORMS': "",
                     'form-0-choice_type': 'choice',
                     'form-0-scores': scores_list,
                     'form-0-question': 'test_question',
                     }
        extra_data = {}
        for num in range(0, nr_answers):
            extra_data['form-0-answer_%s'%num] = 'test answer %s'%num
        post_data.update(extra_data)
        return post_data

    def make_ballot(self, p_uuid):
        p = Poll.objects.get(uuid=p_uuid)
        q_data = p.questions_data[0]
        candidates_to_indexes = q_data['answer_indexes']
        scores_to_indexes = q_data['score_indexes']
        ballot_choices, max_ballot_choices = make_random_range_ballot(
            candidates_to_indexes, scores_to_indexes)
        return ballot_choices, max_ballot_choices

    def test_election_proccess(self):
        self.election_proccess()
