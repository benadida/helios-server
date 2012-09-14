#!/usr/bin/env python
from elgamal import (   Cryptosystem as Crypto,
                        PublicKey, SecretKey, Plaintext, Ciphertext,
                        fiatshamir_challenge_generator  )
from datetime import datetime
from random import randint, shuffle
from collections import defaultdict
from hashlib import sha256
from math import log
from bisect import bisect_right
import Crypto.Util.number as number


from mixnet.EGCryptoSystem import EGCryptoSystem as MixCryptosystem
from mixnet.PublicKey import PublicKey as MixPublicKey
from mixnet.Ciphertext import Ciphertext as MixCiphertext
from mixnet.CiphertextCollection import CiphertextCollection as MixCiphertextCollection

"""
Question 1: Who is your candidate #1?
Answers: [0, ..., C-1]

 [...]

Question i: Who is your candidate #i?
Answers: [1, ..., C-i-1]

 [...]

Question C: Who is your candidate #C?
Answers: [0]
"""


_default_crypto = Crypto()
# from helios/views.py
from cryptosystems import c2048 as crypto

p, q, g, x, y = crypto()
_default_crypto.p = p
_default_crypto.q = q
_default_crypto.g = g

_default_public_key = PublicKey()
_default_public_key.p = _default_crypto.p
_default_public_key.q = _default_crypto.q
_default_public_key.g = _default_crypto.g

_default_secret_key = SecretKey()
_default_secret_key.x = x
_default_secret_key.pk = _default_public_key

_default_public_key.y = y


def get_timestamp():
    return datetime.strftime(datetime.utcnow(), "%Y-%m-%dT%H:%M:%S.%fZ")


def get_choice_params(nr_choices, nr_candidates=None, max_choices=None):
    if nr_candidates is None:
        nr_candidates = nr_choices
    if max_choices is None:
        max_choices = nr_candidates

    if nr_choices < 0 or nr_candidates <= 0 or max_choices <= 0:
        m = ("invalid parameters not (%d < 0 or %d <= 0 or %d <= 0)"
             % (nr_choices, nr_candidates, max_choices))
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


_terms = {}

def get_term(n, k):
    if k >= n:
        return 1

    if n in _terms:
        t = _terms[n]
        if k in t:
            return t[k]
    else:
        t = {n:1}
        _terms[n] = t

    m = k
    while 1:
        m += 1
        if m in t:
            break

    term = t[m]
    while 1:
        term *= m
        m -= 1
        t[m] = term
        if m <= k:
            break

    return term

_offsets = {}

def get_offsets(n):
    if n in _offsets:
        return _offsets[n]

    factor = 1
    offsets = []
    append = offsets.append
    sumus = 0
    i = 0
    while 1:
        sumus += get_term(n, n-i)
        append(sumus)
        if i == n:
            break
        i += 1

    _offsets[n] = offsets
    return offsets

_factors = {}

def get_factor(b, n):
    if n <= 1:
        return 1

    if b in _factors:
        t = _factors[b]
        if n in t:
            return t[n]
    else:
        t = {1: 1}
        _factors[b] = t

    i = n
    while 1:
        i -= 1
        if i in t:
            break

    f = t[i]
    while 1:
        f *= b + i
        i += 1
        t[i] = f
        if i >= n:
            break

    return f

def gamma_encode(choices, nr_candidates=None, max_choices=None):
    nr_choices = len(choices)
    nr_candidates, max_choices = \
        get_choice_params(nr_choices, nr_candidates, max_choices)
    if not nr_choices:
        return 0

    offsets = get_offsets(nr_candidates)
    sumus = offsets[nr_choices - 1]

    b = nr_candidates - nr_choices
    i = 1
    while 1:
        sumus += choices[-i] * get_factor(b, i)
        if i >= nr_choices:
            break
        i += 1

    return sumus

def gamma_decode(sumus, nr_candidates=None, max_choices=None):
    nr_candidates, max_choices = \
        get_choice_params(nr_candidates, nr_candidates, max_choices)

    if sumus <= 0:
        return []

    offsets = get_offsets(nr_candidates)
    nr_choices = bisect_right(offsets, sumus)
    sumus -= offsets[nr_choices - 1]

    choices = []
    append = choices.append
    b = nr_candidates - nr_choices
    i = nr_choices
    while 1:
        choice, sumus = divmod(sumus, get_factor(b, i))
        append(choice)
        if i <= 1:
            break
        i -= 1

    return choices


def verify_gamma_encoding(n, completeness=1):
    choice_sets = {}
    encode_limit = get_offsets(n)[-1]
    encoded_limit = gamma_encode(range(n-1, -1, -1), n) + 1
    if encode_limit != encoded_limit:
        m = "Incorrect encode limit %d vs %d!" % (encode_limit, encoded_limit)
        raise AssertionError(m)

    for encoded in xrange(encode_limit):
        choices = tuple(gamma_decode(encoded, n))
        new_encoded = gamma_encode(choices, n)
        if new_encoded != encoded:
            m = ("Incorrect encoding %s to %d instead of %d"
                    % (choices, new_encoded, encoded))
            raise AssertionError(m)

        if not completeness:
            continue

        nr_choices = len(choices)
        if nr_choices not in choice_sets:
            choice_sets[nr_choices] = set()
        choice_set = choice_sets[nr_choices]
        if choices in choice_set:
            m = ("Duplicate decoding for %d: %s!" % (encoded, choices))
        choice_set.add(choices)


    if not completeness:
        return

    for i in xrange(n + 1):
        if i not in choice_sets:
            m = "Encoding is not bijective! missing choice set %d" % (i,)
            AssertionError(m)

        c = len(choice_sets[i])
        t = get_term(n, n-i)
        if c != t:
            m = ("Encoding is not bijective! "
                 "length-%d choices are %d instead of %d"
                 % (i, c, t))
            raise AssertionError(m)
        print "%d length-%d choices OK" % (c, i)


def factorial_encode(choices, nr_candidates=None, max_choices=None):
    nr_choices = len(choices)
    nr_candidates, max_choices = \
        get_choice_params(nr_choices, nr_candidates, max_choices)

    sumus = 0
    base = nr_candidates + 1
    factor = 1
    for choice in choices:
        choice += 1
        if choice >= base:
            m = ("Cannot vote for %dth candidate when there are only %d remaining"
                    % (choice, base - 1))
            raise ValueError(m)
        sumus += choice * factor
        factor *= base
        base -= 1

    return sumus

def factorial_decode(encoded, nr_candidates=None, max_choices=None):
    nr_candidates, max_choices = \
        get_choice_params(nr_candidates, nr_candidates, max_choices)

    if encoded <= 0:
        return []

    sumus = encoded
    factors = []
    append = factors.append
    base = nr_candidates + 1
    factor = 1

    while factor <= sumus:
        append(factor)
        factor *= base
        base -= 1

    factors.reverse()
    choices = []
    append = choices.append
    for factor in factors:
        choice, sumus = divmod(sumus, factor)
        if choice == 0:
            break
        append(choice - 1)

    if sumus != 0:
        m = ("Invalid encoding %d" % (encoded,))
        raise AssertionError(m)

    nr_choices = len(choices)

    if nr_choices > max_choices:
        m = ("Decoding came up with more choices than allowed: %d > %d"
            % (nr_choices, max_choices))
        raise AssertionError(m)

    choices.reverse()
    return choices


def maxbase_encode(choices, nr_candidates=None, max_choices=None):
    nr_candidates, max_choices = \
        get_choice_params(len(choices), nr_candidates, max_choices)

    base = nr_candidates + 2
    sumus = 0
    e = 1
    for i, choice in enumerate(choices):
        sumus += (choice + 1) * e
        e *= base

    return sumus

def maxbase_decode(sumus, nr_candidates, max_choices=None):
    nr_candidates, max_choices = \
        get_choice_params(nr_candidates, nr_candidates, max_choices)
    choices = []
    append = choices.append

    base = nr_candidates + 2
    while sumus > 0:
        sumus, choice = divmod(sumus, base)
        append(choice - 1)

    return choices


def cross_check_encodings(n):
    # verify_gamma_encoding(n)
    encode_limit = gamma_encode(range(n-1, -1, -1), n) + 1
    for e in xrange(encode_limit):
        choices = gamma_decode(e, n)
        maxbase_encoded = maxbase_encode(choices, n)
        maxbase_choices = maxbase_decode(maxbase_encoded, n)
        factorial_encoded = factorial_encode(choices, n)
        factorial_choices = factorial_decode(factorial_encoded, n)

        if (factorial_choices != maxbase_choices
            or factorial_choices != choices
            or maxbase_choices != choices):

            m = ("gamma_encoded: %d, choices mismatch: "
                 "gamma %s, maxbase %s, factorial %s"
                 % (e, choices, maxbase_choices, factorial_choices))
            raise AssertionError(m)


ballot_encode = gamma_encode
ballot_decode = gamma_decode

def chooser(answers, candidates):
    candidates = list(candidates)
    nr_candidates = len(candidates)
    validate_choices(answers, nr_candidates, nr_candidates)

    rank = []
    append = rank.append
    for answer in answers:
        append(candidates.pop(answer))

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


def sign_message(modulus, base, order, key, message):
    while 1:
        w = number.getRandomRange(3, order)
        r = pow(base, w, modulus) % order
        w = number.inverse(w, order)
        s = w * (message + r*key)
        if s != 0:
            break
    return {'r': r, 's': s, 'm': message}

def verify_signature(modulus, base, order, signature):
    r = signature['r']
    s = signature['s']
    m = signature['m']

    if r <= 0 or r >= order or s <= 0 or s >= order:
        return 0

    u1 = (w * m) % order
    u2 = (w * r) % order
    u = (pow(base, u1, modulus) * pow(base, u2, modulus)) % order
    if u != r:
        return 0

    return 1

def to_relative_answers(choices, nr_candidates):
    """
    Answer choices helper, convert absolute indexed answers to relative.

    e.g. for candidates [A, B, C] absolute choices [1, 2, 0] will be converted
    to [1, 1, 0].
    """
    relative = []
    candidates = list(range(nr_candidates))
    choices = [candidates.index(c) for c in choices]
    for choice in choices:
        index = candidates.index(choice)
        relative.append(index)
        candidates.remove(choice)

    return relative

def to_absolute_answers(choices, nr_candidates):
    """
    Inverts `to_relative_answers` result.
    """
    absolute_choices = []
    candidates = list(range(nr_candidates))
    tmp_cands = candidates[:]
    for choice in choices:
        choice = tmp_cands[choice]
        absolute_choices.append(candidates.index(choice))
        tmp_cands.remove(choice)
    return absolute_choices


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
        self.init_mixnet()

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
        return ("Election (%d candidates / %d votes / %d bits)" %
                (self.nr_candidates, len(self.encrypted_ballots),
                 self.mix_nbits))

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

    @classmethod
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
        return election

    @classmethod
    def from_helios_election_model(cls, election, **kwargs):
        candidates = election.questions[0]['answers']
        max_choices = len(candidates)
        public_key = election.public_key
        name = election.name
        return cls(candidates=candidates, max_choices = max_choices,
              public_key = public_key, name = name, **kwargs)

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
        top = ballot_encode(crange, nr_candidates, max_choices)
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
            if eb['proof']:
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
            vote.sign(_default_secret_key)
            vote.verify_signature()
            owners[owner] = (len(owners), timestamp)

    cast_vote = cast_votes

    def init_mixnet(self):
        pk = self.public_key
        self.mix_nbits = ((int(log(pk.p, 2)) - 1) & ~255) + 256
        self.mix_EG = MixCryptosystem.load(self.mix_nbits, pk.p, pk.g)
        self.mix_pk = MixPublicKey(self.mix_EG, pk.y)

    def mix_ballots(self):
        mix_pk = self.mix_pk
        mix_nbits = self.mix_nbits
        mix_pkfinger = mix_pk.get_fingerprint()
        mix_collection = MixCiphertextCollection(mix_pk)
        add_ciphertext = mix_collection.add_ciphertext
        for v in self.encrypted_ballots:
            ballot = v.encrypted_ballot
            ct = MixCiphertext(mix_nbits, mix_pkfinger)
            ct.append(ballot['a'], ballot['b'])
            add_ciphertext(ct)

        # :mock-mixing, without reencryption, without proof
        # shuffle(ballots)

        mix_shuffled, mix_proof = mix_collection.shuffle_with_proof()
        mix_proof.verify(mix_collection, mix_shuffled)

        ballots = []
        append = ballots.append
        for ct in mix_shuffled:
            encrypted_ballot = {'a': ct.gamma[0], 'b': ct.delta[0]}
            append(Ballot(self, encrypted_ballot=encrypted_ballot))

        self.mixed_ballots = ballots
        return ballots, mix_proof

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
    submission_signature = None

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
        return str(self.answers) if self.answers else "Empty Ballot"

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
        self.ballot_id = ballot_encode(answers, nr_candidates, max_choices)
        self.answers = answers

    def calculate_answers(self, sumus):
        election = self.election
        nr_candidates = election.nr_candidates
        max_choices = election.max_choices
        answers = ballot_decode(sumus, nr_candidates, max_choices)
        validate_choices(answers, nr_candidates, max_choices)
        self.answers = answers
        self.ballot_id = sumus
        return answers

    def verify_ballot_id(self, ballot_id):
        election = self.election
        nr_candidates = election.nr_candidates
        max_choices = election.max_choices
        answers = ballot_decode(sumus, nr_candidates, max_choices)
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

    def get_fingerprint(self):
        h = sha256()
        eb = self.encrypted_ballot
        h.update("%x" % (eb['a']))
        h.update("%x" % (eb['b']))
        h.update("%x" % (eb['proof']))
        f = strbin_to_int(h.digest())
        return f

    def sign(self, secret_key):
        m = self.get_fingerprint()
        k = secret_key.x
        pk = self.election.public_key
        signature = sign_message(pk.p, pk.g, pk.q, k, m)
        self.signature = signature
        return signature

    def verify_signature(self):
        m = self.get_fingerprint()
        s = self.signature
        if m != s['m']:
            return 0
        pk = self.election.public_key
        return verify_signature(pk.p, pk.g, pk.q, s)

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
    from time import time

    argc = len(argv)
    min_candidates = 3
    max_candidates = 5

    if argc >= 2:
        if argv[1] in ('-h', '--help'):
            print ( "Usage: %s [[min_candidates[:max_candidates]]"
                    "[min_voters[:max_voters]]]" % (argv[0],) )
            raise SystemExit

        min_candidates, sep, max_candidates = argv[1].partition(':')
        min_candidates = int(min_candidates)
        if not max_candidates:
            max_candidates = min_candidates
        else:
            max_candidates = int(max_candidates)

    min_voters = min_candidates * min_candidates
    max_voters = max_candidates * max_candidates

    if argc >= 3:
        min_voters, sep, max_voters = argv[2].partition(':')
        min_voters = int(min_voters)
        if not max_voters:
            max_voters = min_voters
        else:
            max_voters = int(max_voters)

    pk = _default_public_key
    sk = _default_secret_key

    c = 0
    stderr.write("\nInterrupt this. It won't stop on its own.\n\n")

    while 1:
        t0 = time()
        nr_votes = randint(min_voters, max_voters)
        election = Election.mk_random(min_candidates=min_candidates,
                                      max_candidates=max_candidates,
                                      public_key=pk)
        votes = []
        for i in xrange(nr_votes):
            stderr.write(" %s: %s: generating %d/%d votes.\r"
                            % (c, election, i, nr_votes))
            v = election.cast_random_votes(1)
            votes.extend(v)

        t1 = time()
        t_generate = t1 - t0
        stderr.write(" %s: %s: generated %d votes in %.1f seconds\n"
                     % (c, election, nr_votes, t_generate))

        stderr.write((" %s: %s: mixing." + " "*30 + "\r") % (c, election))
        election.mix_ballots()
        t2 = time()
        t_mix = t2 - t1
        stderr.write( (" %s: %s: mix complete in %.1f seconds\n")
                       % (c, election, t_mix) )

        append = election.decrypted_ballots.append
        for i, b in enumerate(election.mixed_ballots):
            stderr.write(" %s: %s: decrypting %d/%d votes.\r"
                                % (c, election, i, nr_votes))
            b.decrypt(sk)
            append(b)

        election_results = election.get_results()
        vote_results = count_results(votes)

        t3 = time()
        t_decrypt = t3 - t2
        stderr.write(" %s: %s: decrypted %d votes in %.1f seconds\n"
                            % (c, election, nr_votes, t_decrypt))

        if election_results != vote_results:
            m = "Election corrupt!"
            raise AssertionError(m)

        t_all = t3 - t0
        stderr.write( (" %s: %s: %d votes OK in total %.1f seconds"+" "*30+"\n\n")
                       % (c, election, nr_votes, t_all) )
        c += 1


g = _default_crypto.g
p = _default_crypto.p
q = _default_crypto.q

if __name__ == '__main__':
    import sys
    verify_gamma_encoding(7)
    cross_check_encodings(7)
    main(sys.argv)
    raise KeyboardInterrupt

