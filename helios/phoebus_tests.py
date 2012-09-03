# Phoebus elections tests

import uuid
import tempfile
import os
import json
import random
import pprint

import django_webtest

from django.conf import settings

from auth import models as auth_models
from helios import models
from helios.crypto import elgamal
from helios.crypto.algs import *
from helios.views import ELGAMAL_PARAMS
from helios import utils, datatypes

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
    
    CANDIDATES = ['C1', 'C2', 'C3', 'C4']
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
    
    def _create_election_trustees(self, election, count=1):
        for i in range(count):
            election.generate_trustee(ELGAMAL_PARAMS)

        return election.trustee_set.all()

    def _create_election_questions(self, election):
        questions = []
        positions = len(self.CANDIDATES)
        for question_num in range(positions):
            question = {}
            question['answer_urls'] = [None for x in range(positions)]
            question['choice_type'] = 'approval'
            question['max'] = 1
            question['min'] = 0
            question['question'] = 'Position %d choice' % question_num
            question['answers'] = self.CANDIDATES
            question['result_type'] = 'absolute'
            question['tally_type'] = 'homomorphic'
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
                'legacy/EncryptedVote')
        encrypted_vote = ballot.serialize()
        response = self.app.post("/helios/elections/%s/cast" % election.uuid, {
                'encrypted_vote': encrypted_vote})
        response = self.app.get("/helios/elections/%s/cast_confirm" % election.uuid)
        response.form.submit()
        response = self.app.get("/helios/elections/%s/cast_done" % election.uuid)

    
    def _tally(self, election):
        # log back in as administrator
        self._setup_login(self.admin)

        # encrypted tally
        response = self.client.post("/helios/elections/%s/compute_tally" %
                election.uuid, {
                "csrf_token" : self.client.session['csrf_token']                
                })

        # combine decryptions
        response = self.client.post("/helios/elections/%s/combine_decryptions" %
                election.uuid, {
                "csrf_token" : self.client.session['csrf_token'],
                })

        # check that tally matches
        response = self.client.get("/helios/elections/%s/result" % election.uuid)
        self._clear_login()

        return response.content

    def test_complete_election(self):
        # ballot preparation
        election = self._create_election()
        self._create_election_trustees(election, 1)
        self._create_election_questions(election)
        self._upload_voters(election)

        # freeze election to start voting
        self._freeze_election(election)
        
        # start voting
        FORCE_VOTES = [
                [[1], [0]],
                [[1], [0]],
                [[1], [0]],
        ]
        FORCE_VOTES = []
        
        # place votes, use FORCE_VOTES if index exist else choose randomly
        index = 0
        for voter in models.Voter.objects.filter(election=election):
            vote = []
            if FORCE_VOTES and len(FORCE_VOTES) > index:
                vote = FORCE_VOTES[index]
            else:
                for ind in range(len(self.CANDIDATES)):
                    vote.append([random.choice(range(len(self.CANDIDATES)))])
            index += 1
            self._cast_vote(election, voter, vote)
            
        result = self._tally(election)
        
        # get results
        print
        print "RESULT"
        result_lists = json.loads(result)
        for q_index in range(len(result_lists)):
            print election.questions[q_index]['question']
            for ans_index in range(len(election.questions[q_index]['answers'])):
                cand = election.questions[q_index]['answers'][ans_index]
                votes = result_lists[q_index][ans_index]
                print "Canditate %s was voted %d times" % (cand, votes)
            print
        
        print result_lists
        print models.Election.objects.all()[0].encrypted_tally_hash
    
    def test_crypto(self):
        """
        Dummy crypto methods tests. Useful for helios crypto lib noobs.
        """

        # generate a cyrptosystem (p=128bit)
        cryptosystem = elgamal.Cryptosystem.generate(128)
        
        # generate private(sk)/public(pk) key
        keypair = cryptosystem.generate_keypair()
        pk = keypair.pk
        sk = keypair.sk
        
        # generate plaintexts
        g = 2 # helios use pk.g

        m1 = elgamal.Plaintext(int(math.pow(g, 1) % pk.p), pk)
        m2 = elgamal.Plaintext(int(math.pow(g, 4) % pk.p), pk)
        m3 = elgamal.Plaintext(int(math.pow(g, 2) % pk.p), pk)

        # do the encryption
        ciph1, r1 = pk.encrypt_return_r(m1)
        ciph2, r2 = pk.encrypt_return_r(m2)

        # using custom randomness
        r3 = Utils.random_mpz_lt(pk.q)
        ciph3 = pk.encrypt_with_r(m3, r3)
        
        # calculate factors to use to decode
        factor1 = sk.decryption_factor(ciph1)
        factor2 = sk.decryption_factor(ciph2)
        factor3 = sk.decryption_factor(ciph3)
        
        #
        sumciph = ciph1 * ciph2 * ciph3
        factor = sk.decryption_factor(sumciph)

        newg = sumciph.decrypt([factor], pk)
        self.assertEqual(math.log(newg, g), 7)

    def _cast_js_vote(self, election, voter):
        """
        Casting vote via javascript using python-spidermonkey bindings.
        """

        jsfiles = [
                "js/json2.js",
                "js/underscore-min.js",
                "js/jscrypto/class.js",
                "js/jscrypto/jsbn.js",
                "js/jscrypto/jsbn2.js",
                "js/jscrypto/bigint.dummy.js",
                "js/jscrypto/bigint.js",
                "js/jscrypto/sjcl.js",
                "js/jscrypto/random.js",
                "js/jscrypto/elgamal.js",
                "js/jscrypto/sha1.js",
                "js/jscrypto/sha2.js",
                "js/jscrypto/helios.js"
        ]
        
        class Console(object):
            def log(self, *args):
                print "JS:", args

        base_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "../heliosbooth")
        jscode = "var navigator = {'appName': 'firefox', 'platform': 'linux'};"
        for f in jsfiles:
            jscode = jscode + file(base_dir + "/" + f).read()
        
        # javascript partial from vote.html single page vote app
        vote_code = """;
        BOOTH = {};
        BOOTH.setup_ballot = function(election) {
            BOOTH.ballot = {};
            BOOTH.dirty = [];
            BOOTH.ballot.answers = [];

            BOOTH.election.questions.forEach(function(el, index, array) {
                BOOTH.ballot.answers[index] = [];
                BOOTH.dirty[index] = true;
            });
        };
        
        BOOTH.setup_election = function(raw_json) {
            BOOTH.election = HELIOS.Election.fromJSONString(raw_json);

            BOOTH.election.hash = b64_sha256(raw_json);
            BOOTH.election.election_hash = BOOTH.election.hash

            BOOTH.setup_ballot();
        };

        ;(function() {
            BOOTH.setup_election(JSON.stringify(ELECTION_JSON));
            sjcl.random.addEntropy(RANDOMNESS.randomness);
            
            console.log(BOOTH.election.questions);

            [0,1,2].forEach(function(el, index) {
                console.log("START ENCRYPTION", index);
                BOOTH.ballot.answers = new HELIOS.EncryptedAnswer(
                    BOOTH.election.questions[index], 1, BOOTH.election.public_key);
                BOOTH.ballot.dirty[index] = false;
                console.log("STOP ENCRYPTION", index);
            });

            var sealed = new HELIOS.EncryptedVote(BOOTH.election, 
                BOOTH.ballot.answers, function(){});

            BOOTH.encrypted_ballot = sealed;

            console.log(sealed);
        })();
        """

        # get election json
        self.client.post('/helios/elections/%s/')
        self._setup_voter_login(voter)
        election_json = self.client.get("/helios/elections/%s" % election.uuid)
        randomness_json = self.client.get("/helios/elections/%s/get-randomness" % election.uuid)

        ajax_vars = """;
        ELECTION_JSON = %s;
        RANDOMNESS = %s;
        """ % (election_json.content, randomness_json.content)
        
        import spidermonkey
        cx = spidermonkey.Runtime().new_context()
        cx.add_global("console", Console())
        cx.execute(jscode + ajax_vars + vote_code)
