from elgamal import (   Cryptosystem as Crypto,
                        PublicKey, SecretKey, Plaintext, Ciphertext,
                        fiatshamir_challenge_generator  )
from datetime import datetime
from random import randint, shuffle
from collections import defaultdict
from hashlib import sha256


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
_default_crypto.p = 989739086584899206262870941495275160824429055560857686533827330176266094758539805894052465425543742758378056898916975688830042897464663659316565658681455337631927169716594388227886841821639348093631558865282436882702647379556880510663048896169189712894445414625772725732980365633359489925655152255197807877415565545449245335018149917344244391646710898790373814092708148348289809496148127266128833710713633812316745730790666494269135285419129739194203790948402949190257625314846368819402852639076747258804218169971481348145318863502143264235860548952952629360195804480954275950242210138303839522271423213661499105830190864499755639732898861749724262040063985288535046880936634385786991760416836059387492478292392296693123148006004504907256931727674349140604415435481566616601234362361163612719971993921275099527816595952109693903651179235539510208063074745067478443861419069632592470768800311029260991453478110191856848938562584343057011570850668669874203441257913658507505815731791465642613383737548884273783647521116197224510681540408057273432623662515464447911234487758557242493633676467408119838655147603852339915225523319492414694881196888820764825261617098818167419935357949154327914941970389468946121733826997098869038220817867L
_default_crypto.q = (_default_crypto.p - 1) / 2
_default_crypto.g0 = 905379109279378054831667933021934383049203365537289539394872239929964585601843446288620085443488215849235670964548330175314482714496692320746423694498241639600420478719942396782710397961384242806030551242192462751290192948710587865133212966245479354320246142602442604733345159076201107781809110926242797620743135121644363670775798795477440466184912353407400277976761890802684500243308628180860899087380817190547647023064960578905266420963880594962888959726707822636419644103299943828117478223829675719242465626206333420547052590211049681468686068299735376912002300947541151842072332585948807353379717577259205480481848616672575793598861753734098315126325768793219682113886710293716896643847366229743727909553144369466788439959883261553813689358512428875932488880462227384092880763795982392286068303024867839002503956419627171380097115921561294617590444883631704182199378743252195067113032765888842970561649353739790451845746283977126938388768194155261756458620157130236063008120298689861009201257816492322336749660466823368953374665392072697027974796990473518319104748485861774121624711704031122201281866933558898944724654566536575747335471017845835905901881155585701928903481835039679354164368715779020008195518681150433222291955165L
_default_crypto.g = pow(_default_crypto.g0, 2, _default_crypto.p)

_default_public_key = PublicKey()
_default_public_key.p = _default_crypto.p
_default_public_key.q = _default_crypto.q
_default_public_key.g = _default_crypto.g

_default_secret_key = SecretKey()
_default_secret_key.x = 647933544049795511827798129172072110981142881302659046504851880714758189954678388061140591638507897688860150172786162388977702691017897290499481587217235024527398988456841084908316048392761588172586494519258100136278585068551347732010458598151493508354286285844575102407190886593809138094472405420010538813082865337021620149988134381297015579494516853390895025461601426731339937104058096140467926750506030942064743367210283897615531268109510758446261715511997406060121720139820616153611665890031155426795567735688778815148659805920368916905139235816256626015209460683662523842754345740675086282580899535810538696220285715754930732549385883748798637705838427072703804103334932744710977146180956976178075890301249522417212403111332457542823335873806433530059450282385350277072533852089242268226463602337771206993440307129522655918026737300583697821541073342234103193338354556016483037272142964453985093357683693494958668743388232300130381063922852993385893280464288436851062428165061787405879100666008436508712657212533042512552400211216182296391299371649632892185300062585730422510058896752881990053421349276475246102235172848735409746894932366562445227945573810219957699804623611666670328066491935505098459909869015330820515152531557L
_default_secret_key.pk = _default_public_key

_default_public_key.y = pow(_default_public_key.g,
                            _default_secret_key.x,
                            _default_public_key.p)


def get_timestamp():
    return datetime.strftime(datetime.utcnow(), "%Y-%m-%dT%H:%M:%S.%fZ")


def get_choice_params(nr_choices, nr_candidates=None, max_choices=None):
    if nr_candidates is None:
        nr_candidates = nr_choices
    if max_choices is None:
        max_choices = nr_candidates

    if nr_choices <= 0 or nr_candidates <= 0 or max_choices <= 0:
        m = ("choice encoding needs positive parameters, "
             "not (%d, %d, %d)" % (nr_choices, nr_candidates, max_choices))
        raise ValueError(m)

    if nr_choices > max_choices:
        m = ("Invalid number of choices (%d expected up to %d)" %
             (nr_choices, max_choices))
        raise AssertionError(m)

    return nr_candidates, max_choices

def validate_choices(choices, nr_candidates=None, max_choices=None):
    nr_candidates, max_choices = \
        get_choice_params(len(choices), nr_candidates, max_choices)

    choice_iter = iter(enumerate(choices))

    for i, choice in choice_iter:
        m = nr_candidates - i
        if choice < 0 or choice > m:
            m = "Choice #%d: %d not in range [%d, %d]" % (i, choice, 0, m)
            raise AssertionError(m)

        if choice == 0:
            nzi = i
            for i, choice in choice_iter:
                if choice != 0:
                    m = ("Choice #%d is nonzero (%d) after zero choice #%d" %
                         (i, choice, nzi))
                    raise AssertionError(m)
            return 1

        m -= 1

    return 1

def factorial_encode(choices, nr_candidates=None, max_choices=None):
    nr_candidates, max_choices = \
        get_choice_params(len(choices), nr_candidates, max_choices)

    sumus = 1
    base = nr_candidates
    factor = 1
    for choice in choices:
        if choice == 0:
            break
        if choice >= base:
            m = ("Cannot vote for %dth candidate when there are only %d remaining"
                    % (choice+1, base))
            raise ValueError(m)
        sumus += choice * factor
        factor *= base
        base -= 1

    return sumus

def factorial_decode(sumus, nr_candidates=None, max_choices=None):
    nr_candidates, max_choices = \
        get_choice_params(nr_candidates, nr_candidates, max_choices)

    factors = []
    append = factors.append
    base = nr_candidates
    factor = 1
    sumus -= 1

    for _ in xrange(max_choices):
        append(factor)
        factor *= base
        base -= 1

    factors.reverse()
    choices = []
    append = choices.append
    for factor in factors:
        choice, sumus = divmod(sumus, factor)
        append(choice)

    nr_choices = len(choices)
    if nr_choices > max_choices:
        m = ("Decoding came up with more choices than expected: %d > %d" % 
             (nr_choices, max_choices))
        raise AssertionError(m)

    if sumus > nr_candidates:
        m = ("Decoding run out of factors "
             "while sumus is still too high: %d > %d" % (sumus, nr_candidates))
        raise AssertionError(m)

    choices.reverse()
    return choices


def maxbase_encode(choices, nr_candidates=None, max_choices=None):
    nr_candidates, max_choices = \
        get_choice_params(len(choices), nr_candidates, max_choices)

    base = nr_candidates + 1
    sumus = 0
    e = 1
    for i, choice in enumerate(choices):
        sumus += choice * e
        e *= base

    return sumus

def maxbase_decode(sumus, nr_candidates, max_choices=None):
    nr_candidates, max_choices = \
        get_choice_params(nr_candidates, nr_candidates, max_choices)
    choices = []
    append = choices.append

    base = nr_candidates + 1
    while sumus > 0:
        sumus, choice = divmod(sumus, base)
        append(choice)

    choices += [0] * (nr_candidates - len(choices))

    return choices


def chooser(answers, candidates):
    candidates = list(candidates)
    nr_candidates = len(candidates)
    tmp_answers = answers + [0] * (nr_candidates - len(answers))
    validate_choices(tmp_answers, nr_candidates, nr_candidates)

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


def count_results(ballots):
    results = defaultdict(int)
    for b in ballots:
        answers = tuple(b.answers)
        results[answers] += 1
    return sorted(results.items())


def strbin_to_int(string):
    # lsb
    s = 0
    base = 1
    for c in string:
        s += ord(c) * base
        base *= 256

    return s

def hash_to_commitment_and_challenge(alpha, beta):
    h = sha256()
    h.update(hex(alpha))
    ha = strbin_to_int(h.digest())
    h = sha256()
    h.update(hex(beta))
    hb = strbin_to_int(h.digest())
    commitment = (ha >> 128) | ((hb << 128) & (2**256-1))
    challenge = (hb >> 128) | ((ha << 128) & (2**256-1))

    return commitment, challenge

def prove_encryption(modulus, alpha, beta, randomness):
    commitment, challenge = hash_to_commitment_and_challenge(alpha, beta)
    response = (commitment + challenge * randomness)
    return response

def verify_encryption(modulus, base, alpha, beta, proof):
    commitment, challenge = hash_to_commitment_and_challenge(alpha, beta)
    return (pow(base, proof, modulus) == 
            (pow(base, commitment, modulus) *
             pow(alpha, challenge, modulus) % modulus))


class InvalidVoteError(Exception):
    pass


class Election(object):

    candidates = None
    public_key = None
    encrypted_ballots = None
    mixed_ballots = None
    decrypted_ballots = None

    max_choices = None

    _powers = None
    _logs = None
    _ballot_owners = None

    _generic_elections = {}


    def __init__(self,  candidates,
                        public_key                      =   None,
                        max_choices                     =   None,
                        name                            =   None,
                        encrypted_ballots               =   None,
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

        if max_choices is not None:
            self.max_choices = max_choices

        if name is None:
            name = 'election_' + get_timestamp()

        self.name = name

        self.encrypted_ballots = []
        if encrypted_ballots is not None:
            self.cast_votes(encrypted_ballots)

        self.mixed_ballots = []
        if mixed_ballots is not None:
            self.mixed_ballots = mixed_ballots

        self.decrypted_ballots = []

        self._powers = {}
        if _powers is not None:
            self._powers.update(_powers)

        self._logs = {}
        if _logs is not None:
            self._logs.update(_logs)

        self.validate_cryptosystem()

    def validate_cryptosystem(self):
        from Crypto.Util.number import isPrime
        pk = self.public_key
        if pow(pk.g, pk.q, pk.p) != 1:
            m = "g is not a generator, or q is not its order!"
            raise AssertionError(m)

        if not isPrime(pk.p):
            m = "modulus not prime!"
            raise AssertionError(m)

        if not isPrime(pk.q):
            m = "subgroup order not prime!"
            raise AssertionError(m)

        if 2*pk.q + 1 != pk.p:
            m = "modulus not in the form 2*(prime subgroup order) + 2"
            raise AssertionError(m)

        return 1

    def __str__(self):
        return ("Election (%d candidates / %d votes)" % 
                (self.nr_candidates, len(self.encrypted_ballots)))

    __repr__ = __str__

    def to_dict(self):
        return {
                'candidates'                :   self.candidates,
                'name'                      :   self.name,
                'public_key'                :   pk_to_dict(self.public_key),
                'max_choices'               :   self.max_choices,
                'encrypted_ballots'         :   self.encrypted_ballots,
                'mixed_ballots'             :   self.mixed_ballots,
                '_powers'                   :   self._powers,
                '_logs'                     :   self._logs,
               }

    def get_generic_election(cls, nr_candidates, max_choices, pk):
        elections = cls._generic_elections
        if (max_choices is None
            or max_choices <= 0
            or max_choices > nr_candidates):

            max_choices = nr_candidates

        key = (nr_candidates, max_choices, pk.p, pk.g, pk.q, pk.y)
        if key in elections:
            return elections[key]

        candidates = ["Candidate #%d" % x for x in xrange(nr_candidates)]
        public_key = PublicKey()
        public_key.p = pk.p
        public_key.g = pk.g
        public_key.q = pk.q
        public_key.y = pk.y

        election = Election(candidates,
                            max_choices     =   max_choices,
                            public_key      =   public_key)
        elections[key] = election

    @classmethod
    def from_dict(cls, dict_object):
        ob = dict(dict_object)
        pk = ob.pop('public_key')
        if pk is not None:
            pk = pk_from_dict(pk)
        candidates = ob.pop('candidates')
        election = Election(candidates, public_key=pk, **ob)
        return election

    @classmethod
    def mk_random(cls,  min_candidates  =   3,
                        max_candidates  =   10,
                        min_voters      =   10,
                        max_voters      =   50,
                        public_key      =   None):

        candidate_range = xrange(randint(min_candidates, max_candidates))
        candidates = ["Candidate #%d" % x for x in candidate_range]
        election = cls(candidates, public_key=public_key)

        return election

    def cast_random_votes(self, nr):
        ballots = [Ballot.mk_random(self) for _ in xrange(nr)]
        self.cast_votes(ballots)
        return ballots

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

    def q_encode(self, m):
        pk = self.public_key
        m += 1 # this is to avoid element 0 when m == 0
        legendre = pow(m, pk.q, pk.p)
        if legendre == 1:
            return m
        else:
            return -m % pk.p
            
    def q_decode(self, m):
        pk = self.public_key
        if m > q:
            m = -m % pk.p
        return m - 1

    def generate_discrete_logs(self):
        nr_candidates = self.nr_candidates
        max_choices = self.max_choices
        crange = range(nr_candidates, nr_candidates-max_choices, -1)
        top = factorial_encode(crange, nr_candidates, max_choices)
        pk = self.public_key
        g = pk.g
        n = 1
        p = pk.p
        logs = self._logs
        powers = self._powers

        for i in xrange(top):
            if i in powers:
                continue

            powers[i] = n
            logs[n] = i
            n *= g
            print "%d / %d" % (i, top)

    def cast_votes(self, votes=None):
        if votes is None:
            m = "Add votes expects a vote or list of votes as argument)"
            raise ValueError(m)

        if isinstance(votes, Ballot):
            votes = [votes]

        owners = self._ballot_owners
        if owners is None:
            owners = {}
            self._ballot_owners = owners

        nr_candidates = self.nr_candidates
        pk = self.public_key

        ballot_append = self.encrypted_ballots.append

        for vote in votes:
            owner = vote.owner
            eb = vote.encrypted_ballot
            if not verify_encryption(pk.p, pk.g, eb['a'], eb['b'], eb['proof']):
                m = ("Invalid encryption proof for vote #%d, from %s"
                        % (len(owners), owner))
                raise InvalidVoteError(m)

            timestamp = get_timestamp()
            if owner in owners:
                m = ("Owner %s attempts to vote again. "
                     "Original vote was #%d at %s, second attempt (now) #%d."
                     % (owner, onwers[owner][0], owners[owner][1],
                        len(owners), timestamp))

                raise InvalidVoteError(m)

            # FIXME: verification?

            ballot_append(vote)
            owners[owner] = (len(owners), timestamp)

    cast_vote = cast_votes

    def mix_ballots(self):
        ballots = []
        append = ballots.append
        for v in self.encrypted_ballots:
            b = Ballot(self, encrypted_ballot=v.encrypted_ballot)
            append(b)

        # FIXME >>
        # :mock-mixing, without reencryption, without proof
        shuffle(ballots)
        # << FIXME

        self.mixed_ballots = ballots
        return ballots

    def decrypt_ballots(self, secret_key):
        # FIXME: This should be split into several calls of partial_decrypt
        # from trustee input with proofs, followed by a final combine decryptions
        # operation in-server.

        decrypted_ballots = [b.decrypt(secret_key) for b in self.mixed_ballots]
        self.decrypted_ballots = decrypted_ballots
        return decrypted_ballots

    def get_results(self):
        return count_results(self.decrypted_ballots)


class Ballot(object):
    election = None
    owner = None
    answers = None
    ballot_id = None
    encryption_random = None
    encrypted_ballot = None

    _owner_count = 0

    def __init__(self,  election,
                        answers             =   None,
                        ballot_id           =   None,
                        encrypted_ballot    =   None,
                        owner               =   None,
                        secret_key          =   None,
                ):

        self.election = election

        if answers is not None:
            self.calculate_ballot_id(answers)
            self.encrypt()

        elif ballot_id is not None:
            self.answers = self.calculate_answers(ballot_id)
            self.encrypt()

        elif encrypted_ballot is not None:
            self.encrypted_ballot = encrypted_ballot
            if secret_key is not None:
                self.decrypt(secret_key)
        else:
            m = ("%s: Neither answers, nor ballot_id, "
                 "nor encrypted_ballot given" % (type(self),))
            raise ValueError(m)

        if owner is None:
            owner = self._get_owner()

        self.owner = owner

    @classmethod
    def _get_owner(cls):
        counter = cls._owner_count + 1
        cls._owner_count = counter
        return counter

    def to_dict(self):
        election = self.election
        return {
                'nr_candidates'     : election.nr_candidates,
                'max_choices'       : election.max_choices,
                'public_key'        : pk_to_dict(election.public_key),
                'answers'           : self.answers,
                'ballot_id'         : self.ballot_id,
                'encrypted_ballot'  : self.encrypted_ballot,
               }

    def __str__(self):
        return str(self.answers)

    __repr__ = __str__

    @classmethod
    def from_dict(cls, dict_object, election=None):
        ob = dict(dict_object)
        nr_candidates = ob.pop('nr_candidates')
        max_choices = ob.pop('max_choices')
        public_key = ob.pop('public_key')
        election = Election.get_generic_election(   nr_candidates,
                                                    max_choices,
                                                    public_key  )
        return Ballot(election, **ob)

    @classmethod
    def mk_random(cls, election):
        answers = []
        append = answers.append
        z = 0
        for m in xrange(election.nr_candidates-1, -1, -1):
            r = randint(0, m)
            if r == 0:
                z = 1
            if z:
                append(0)
            else:
                append(r)

        ballot = cls(election, answers=answers)
        return ballot

    def calculate_ballot_id(self, answers):
        election = self.election
        nr_candidates = election.nr_candidates
        max_choices = election.max_choices

        validate_choices(answers, nr_candidates, max_choices)
        self.ballot_id = factorial_encode(answers, nr_candidates, max_choices)
        self.answers = answers

    def calculate_answers(self, sumus):
        election = self.election
        nr_candidates = election.nr_candidates
        max_choices = election.max_choices
        answers = factorial_decode(sumus, nr_candidates, max_choices)
        validate_choices(answers, nr_candidates, max_choices)
        self.answers = answers
        self.ballot_id = sumus
        return answers

    def verify_ballot_id(self, ballot_id):
        election = self.election
        nr_candidates = election.nr_candidates
        max_choices = election.max_choices
        answers = factorial_decode(sumus, nr_candidates, max_choices)
        if answers != self.answers:
            m = ("Ballot id: %d corresponds to answers %s, "
                 "which do not correspond to ballot answers %s",
                 (self.ballot_id, answers, self.answers))
            raise AssertionError(m)
        return 1

    def encode(self):
        enc = self.election.q_encode
        encoded_ballot = enc(self.ballot_id)
        self.encoded_ballot = encoded_ballot
        return encoded_ballot

    def decode(self):
        dec = self.election.q_decode
        ballot_id = dec(self.encoded_ballot)
        answers = self.calculate_answers(ballot_id)
        return ballot_id, answers

    def encrypt(self):
        encoded_ballot = self.encode()

        pk = self.election.public_key
        c, r = pk.encrypt_return_r(Plaintext(encoded_ballot, pk))
        encryption_random = r
        proof = prove_encryption(pk.p, c.alpha, c.beta, encryption_random)
        encrypted_ballot = {'a': c.alpha, 'b': c.beta, 'proof': proof}
        self.encryption_random = encryption_random
        self.encrypted_ballot = encrypted_ballot

        return encrypted_ballot, encryption_random

    def _decrypt(self, secret_key, encrypted_ballot):
        eb = self.encrypted_ballot
        ct = Ciphertext(alpha=eb['a'], beta=eb['b'], pk=secret_key.pk)
        encoded_ballot = secret_key.decrypt(ct).m
        return encoded_ballot

    def decrypt(self, secret_key):
        encoded_ballot = self._decrypt(secret_key, self.encrypted_ballot)
        self.encoded_ballot = encoded_ballot
        ballot_id, answers = self.decode()
        return ballot_id, answers


def main(argv):
    from sys import stderr
    argc = len(argv)
    pk = _default_public_key
    sk = _default_secret_key

    c = 0
    stderr.write("\nInterrupt this. It won't stop on its own.\n\n")

    while 1:
        nr_votes = randint(20, 300)
        election = Election.mk_random(public_key=pk)
        votes = []
        for i in xrange(nr_votes):
            stderr.write(" %s: %s: generating %d/%d votes.\r"
                            % (c, election, i, nr_votes))
            v = election.cast_random_votes(1)
            votes.extend(v)
        stderr.write((" %s: %s: mixing." + " "*30 + "\r") % (c, election))
        election.mix_ballots()
        append = election.decrypted_ballots.append
        for i, b in enumerate(election.mixed_ballots):
            stderr.write(" %s: %s: decrypting %d/%d votes.\r"
                                % (c, election, i, nr_votes))
            b.decrypt(sk)
            append(b)

        election_results = election.get_results()
        vote_results = count_results(votes)
        if election_results != vote_results:
            m = "Election corrupt!"
            raise AssertionError(m)

        stderr.write((" %s: %s: %d votes OK." + " "*30 +"\n")
                        % (c, election, nr_votes))
        c += 1


g = _default_crypto.g
p = _default_crypto.p
q = _default_crypto.q

if __name__ == '__main__':
    import sys
    main(sys.argv)
    raise KeyboardInterrupt

