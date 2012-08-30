from elgamal import (   Cryptosystem as Crypto,
                        PublicKey, SecretKey, Plaintext, Ciphertext )
from datetime import datetime
from random import randint


"""
Assume C := { the candidates }, V := { the voters }

mc1, mc2 = MixProof(c1, c2)


Question 1: Who is your candidate #1?
Answers: [0, 1, ..., C]

 [...]

Question i: Who is your candidate #i?
Answers: [0, 1, ..., C-i]

 [...]

Question C: Who is your candidate #C?
Answers: [0, 1]
"""


_default_crypto = Crypto()
# from helios/views.py
_default_crypto.p = 16328632084933010002384055033805457329601614771185955389739167309086214800406465799038583634953752941675645562182498120750264980492381375579367675648771293800310370964745767014243638518442553823973482995267304044326777047662957480269391322789378384619428596446446984694306187644767462460965622580087564339212631775817895958409016676398975671266179637898557687317076177218843233150695157881061257053019133078545928983562221396313169622475509818442661047018436264806901023966236718367204710755935899013750306107738002364137917426595737403871114187750804346564731250609196846638183903982387884578266136503697493474682071L
_default_crypto.q = 61329566248342901292543872769978950870633559608669337131139375508370458778917L
_default_crypto.g = 14887492224963187634282421537186040801304008017743492304481737382571933937568724473847106029915040150784031882206090286938661464458896494215273989547889201144857352611058572236578734319505128042602372864570426550855201448111746579871811249114781674309062693442442368697449970648232621880001709535143047913661432883287150003429802392229361583608686643243349727791976247247948618930423866180410558458272606627111270040091203073580238905303994472202930783207472394578498507764703191288249547659899997131166130259700604433891232298182348403175947450284433411265966789131024573629546048637848902243503970966798589660808533L

_default_public_key = PublicKey()
_default_public_key.p = _default_crypto.p
_default_public_key.q = _default_crypto.q
_default_public_key.g = _default_crypto.g
_default_public_key.y = 15752247830805804912891895067983863708641951708622563698749548842710959111594837427699129574136148142778404066040080012100955666588876339993757253608303306917556983345172006360971649356214390161558469295972805316042112738094451900758381809171615212679610277861594064545194620302295070661687536116703857265517447715085616574085047110216120378087285393287524418178732598479379068663326976423143930670655703854058754144298505395833522229417929975119436324762829865223699924094541940022050471370482190252653251106164751513447032295381462205606296487183515081985928293836983180955255466653480129504113651912683919886819261L

_default_secret_key = SecretKey()
_default_secret_key.x = 14440796396454537139238978260895408751602831750485722702456204117522709343715084985557340843202535209090566236411053616668607920132443989871725032264936882615892796841394092608037798851554381197018895602786660416585531945020912138573840211710430565840571514533148841925524631646807307331443712178213698951623133241428833259673223706329253219802058426024068312398950487866217936433694412143721016640090834137248934937823870717024923102228435264516049217897694931863209124779907334592407104790330505924564673506465448776345554958208325303284562366817863201678926430163196635224732434534526862591186948557949140656296805L
_default_secret_key.pk = _default_public_key


def validate_answers(answers, nr_candidates, max_votes=None):
    if max_votes is None or max_votes > nr_candidates or max_votes < 0:
        max_votes = nr_candidates

    if len(answers) != max_votes:
        m = ("Invalid number of answers (%d expected %d)"
                % (len(answers), nr_candidates))
        raise AssertionError(m)

    answer_iter = iter(enumerate(answers))
    for i, answer in answer_iter:
        m = nr_candidates - i
        if answer < 0 or answer > m:
            m = "Answer %d: %d not in range [%d, %d]" % (i, answer, 0, m)
            raise AssertionError(m)

        if answer == 0:
            nzi = i
            for i, answer in answer_iter:
                if answer != 0:
                    m = ("Answer %d is nonzero (%d) after zero answer %d"
                            % (i, answer, nzi))
                    raise AssertionError(m)
            return 1

        m -= 1

    return 1


def chooser(answers, candidates):
    candidates = list(candidates)
    nr_candidates = len(candidates)
    tmp_answers = answers + [0] * (nr_candidates - len(answers))
    validate_answers(tmp_answers, nr_candidates)

    rank = []
    append = rank.append
    for answer in answers:
        if answer == 0:
            break
        append(candidates.pop(answer-1))

    return rank, candidates


def pk_to_dict(pk):
    if pk is None:
        return None

    return {
            'p': pk.p,
            'q': pk.q,
            'g': pk.g,
            'y': pk.y,
           }

def pk_from_dict(dict_object):
    pk = PublicKey()
    pk.g = dict_object['p']
    pk.q = dict_object['q']
    pk.g = dict_object['g']
    pk.y = dict_object['y']
    return pk


def sk_to_dict(sk):
    if sk is None:
        return None
    return {
            'x': sk.x,
            'pk': pk_to_dict(sk.pk),
           }

def sk_from_dict(dict_object):
    sk = SecretKey()
    sk.x = dict_object['x']
    sk.pk = pk_from_dict(dict_object['pk'])
    return sk


class Election(object):

    candidates = None
    public_key = None
    encrypted_answers = None
    encrypted_answer_proofs = None
    encrypted_ballots = None
    mixed_encrypted_ballots = None
    mixed_encrypted_ballot_proofs = None
    mixed_ballots = None

    max_votes = None

    _powers = None
    _logs = None

    def __init__(self,  candidates,
                        public_key                      =   None,
                        max_votes                       =   None,
                        name                            =   None,
                        encrypted_answers               =   None,
                        encrypted_answers_proofs        =   None,
                        encrypted_ballots               =   None,
                        mixed_encrypted_ballots         =   None,
                        mixed_encrypted_ballots_proofs  =   None,
                        mixed_ballots                   =   None,
                        _powers                         =   None,
                        _logs                           =   None):

        self._powers = {}
        self._logs = {}

        candidates = list(set(candidates))
        candidates.sort()
        self.candidates = candidates
        C = len(candidates)
        self.C = C
        self.nr_candidates = C
        if public_key is None:
            public_key = _default_public_key
        self.public_key = public_key

        if max_votes is not None:
            self.max_votes = max_votes

        if name is None:
            name = datetime.strftime(datetime.utcnow(), "%Y-%m-%dT%H:%M:%S.%fZ")

        self.name = name

        if encrypted_answers is not None:
            self.encrypted_answers = encrypted_answers

        if encrypted_answers_proofs is not None:
            self.encrypted_answers_proofs = encrypted_answers_proofs

        if encrypted_ballots is not None:
            self.encrypted_ballots = encrypted_ballots

        if mixed_encrypted_ballots is not None:
            self.mixed_encrypted_ballots = mixed_encrypted_ballots

        if mixed_encrypted_ballots_proofs is not None:
            self.mixed_encrypted_ballots_proofs = mixed_encrypted_ballots_proofs

        if mixed_ballots is not None:
            self.mixed_ballots = mixed_ballots

        if _powers is not None:
            self._powers = _powers

        if _logs is not None:
            self._logs = _logs


    def to_dict(self):
        return {
                'candidates'                :   self.candidates,
                'name'                      :   self.name,
                'public_key'                :   pk_to_dict(self.public_key),
                'max_votes'                 :   self.max_votes,
                'encrypted_answers'         :   self.encrypted_answers,
                'encrypted_ballots'         :   self.encrypted_ballots,
                'mixed_encrypted_ballots'   :   self.mixed_encrypted_ballots,
                'mixed_ballots'             :   self.mixed_ballots,
                '_powers'                   :   self._powers,
                '_logs'                     :   self._logs,
               }

    @classmethod
    def from_dict(cls, dict_object):
        pk = dict_object.pop('public_key')
        if pk is not None:
            pk = pk_from_dict(pk)
        candidates = dict_object.pop('candidates')
        election = Election(candidates, public_key=pk, **dict_object)
        return election

    @classmethod
    def mk_random(cls):
        candidates = ["Candidate #%d" % x for x in xrange(randint(3, 10))]
        election = cls(candidates)
        ballots = [Ballot.mk_random(election) for x in xrange(randint(10, 100))]
        election.encrypted_ballots = ballots
        return election

    def g_encode(self, n):
        powers = self._powers
        if n in powers:
            return powers[n]

        pk = self.public_key
        p = pow(pk.g, n, pk.p)
        powers[n] = p
        self._logs[p] = n
        return p

    def g_decode(self, p):
        logs = self._logs
        if p in logs:
            return logs[p]

        # No hope.
        m = ("Can't calculate discrete log if it isn't already "
             "cached from exponentiation (g_encode())!")
        raise ValueError(m)


class Ballot(object):
    election = None
    answers = None
    ballot_id = None
    secret_key = None
    encoded_answers = None
    encrypted_answers = None
    encryption_randoms = None
    encrypted_ballot = None
    encrypted_ballot_randomness = None

    def __init__(self,  election,
                        answers             =   None,
                        ballot_id           =   None,
                        encrypted_ballot    =   None,
                        encrypted_answers   =   None,
                        secret_key          =   None):

        self.election = election
        if ballot_id is not None:
            ballod_id = None

        if answers is not None:
            self.calculate_ballot_id(answers)
            self.encrypt()

        elif ballot_id is not None:
            self.ballot_id = ballot_id
            self.answers = self.calculate_answers()
            self.encrypt()

        elif encrypted_ballot is not None:
            self.encrypted_ballot = encrypted_ballot
            if secret_key is not None:
                self.decrypt(secret_key)

        else:
            m = ("%s(): Neither answers, nor ballot_id, "
                 "nor encrypted_ballot given" % (type(self),))
            raise ValueError(m)

        if encrypted_answers is not None:
            self.encrypted_answers = encrypted_answers


    def to_dict(self):
        return {
                'election'          : self.election.to_dict(),
                'answers'           : self.answers,
                'ballot_id'         : self.ballot_id,
                'encrypted_ballot'  : self.encrypted_ballot,
                'encrypted_answers' : self.encrypted_answers,
                'secret_key'        : sk_to_dict(self.secret_key),
               }

    def __str__(self):
        return str(self.answers)

    __repr__ = __str__

    @classmethod
    def from_dict(cls, dict_object):
        election = Election.from_dict(dict_object.pop('election'))
        sk = dict_object.pop('secret_key', None)
        if sk is not None:
            sk = sk_from_dict(sk)
            dict_object['secret_key'] = sk

        return Ballot(election, **dict_object)

    @classmethod
    def mk_random(cls, election):
        answers = []
        append = answers.append
        z = 0
        for m in xrange(election.nr_candidates, 0, -1):
            r = randint(0, m)
            if r == 0:
                z = 1
            if z:
                append(0)
            else:
                append(r)

        ballot = cls(election, answers)
        return ballot

    def calculate_ballot_id(self, answers):
        election = self.election
        nr_candidates = election.nr_candidates
        max_votes = election.max_votes

        base = nr_candidates + 1
        sumus = 0
        e = 1
        for i, answer in enumerate(answers):
            sumus += answer * e
            e *= base

        self.answers = answers
        self.ballot_id = sumus

    def calculate_answers(self):
        base = self.election.nr_candidates + 1
        answers = []
        append = answers.append
        sumus = self.ballot_id

        while sumus > 0:
            sumus, answer = divmod(sumus, base)
            append(answer)

        validate_answers(answers, base - 1)
        return answers

    def verify_ballot_id(self):
        answers = self.calculate_answers()
        if answers != self.answers:
            m = ("Ballot id: %d corresponds to answers %s, "
                 "which do not correspond to ballot answers %s",
                 (self.ballot_id, answers, self.answers))
            raise AssertionError(m)
        return 1

    def encode(self):
        enc = self.election.g_encode
        encoded_answers = []
        append = encoded_answers.append

        for answer in self.answers:
            append(enc(answer))

        self.encoded_answers = encoded_answers

        encoded_ballot = enc(self.ballot_id)
        self.encoded_ballot = encoded_ballot

        return encoded_ballot, encoded_answers

    def decode(self):
        answers = []
        append = answers.append
        dec = self.election.g_decode
        for encoded in self.encoded_answers:
            append(dec(encoded))

        answers = answers
        self.calculate_ballot_id(answers)

        ballot_id = dec(self.encoded_ballot)

        return ballot_id, answers

    def encrypt(self):
        pk = self.election.public_key

        encrypted_answers = []
        cipher_append = encrypted_answers.append
        encryption_randoms = []
        random_append = encryption_randoms.append

        encoded_answers = self.encoded_answers
        if encoded_answers is None:
            encoded_ballot, encoded_answers = self.encode()

        encrypt = pk.encrypt_return_r
        for encoded in self.encoded_answers:
            c, r = encrypt(Plaintext(encoded, pk))
            cipher_append({'a': c.alpha, 'b': c.beta})
            random_append(r)

        c, r = encrypt(Plaintext(encoded_ballot, pk))
        encrypted_ballot = {'a': c.alpha, 'b': c.beta}
        encrypted_ballot_randomness = r

        self.encrypted_answers = encrypted_answers
        self.encryption_randoms = encryption_randoms
        self.encrypted_ballot = encrypted_ballot
        self.encrypted_ballot_randomness = encrypted_ballot_randomness

        return encrypted_ballot, encrypted_answers, encryption_randoms

    def decrypt(self, secret_key):
        self.secret_key = secret_key
        pk = secret_key.pk

        dec = self.election.g_decode
        decrypt = secret_key.decrypt

        eb = self.encrypted_ballot
        c = Ciphertext(alpha=eb['a'], beta=eb['b'], pk=pk)
        encoded_ballot = decrypt(c).m
        ballot_id = dec(encoded_ballot)
        self.encoded_ballot = encoded_ballot
        self.ballot_id = ballot_id
        self.calculate_answers()

        return ballot_id, answers

# rb = Ballot(Election(["c", "b", "d", "a"]), [3, 3, 2, 1])
# e.verify_ballot_id()

