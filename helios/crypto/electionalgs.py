"""
Election-specific algorithms for Helios

Ben Adida
2008-08-30
"""

import algs
import logging
import utils
import uuid
import datetime

class HeliosObject(object):
  """
  A base class to ease serialization and de-serialization
  crypto objects are kept as full-blown crypto objects, serialized to jsonobjects on the way out
  and deserialized from jsonobjects on the way in
  """
  FIELDS = []
  JSON_FIELDS = None

  def __init__(self, **kwargs):
    self.set_from_args(**kwargs)

    # generate uuid if need be
    if 'uuid' in self.FIELDS and (not hasattr(self, 'uuid') or self.uuid == None):
      self.uuid = str(uuid.uuid4())

  def set_from_args(self, **kwargs):
    for f in self.FIELDS:
      if kwargs.has_key(f):
        new_val = self.process_value_in(f, kwargs[f])
        setattr(self, f, new_val)
      else:
        setattr(self, f, None)

  def set_from_other_object(self, o):
    for f in self.FIELDS:
      if hasattr(o, f):
        setattr(self, f, self.process_value_in(f, getattr(o,f)))
      else:
        setattr(self, f, None)

  def toJSON(self):
    return utils.to_json(self.toJSONDict())

  def toJSONDict(self, alternate_fields=None):
    val = {}
    for f in (alternate_fields or self.JSON_FIELDS or self.FIELDS):
      val[f] = self.process_value_out(f, getattr(self, f))
    return val

  @classmethod
  def fromJSONDict(cls, d):
    # go through the keys and fix them
    new_d = {}
    for k in d.keys():
      new_d[str(k)] = d[k]

    return cls(**new_d)

  @classmethod
  def fromOtherObject(cls, o):
    obj = cls()
    obj.set_from_other_object(o)
    return obj

  def toOtherObject(self, o):
    for f in self.FIELDS:
      # FIXME: why isn't this working?
      if hasattr(o, f):
        # BIG HAMMER
        try:
          setattr(o, f, self.process_value_out(f, getattr(self,f)))
        except:
          pass

  @property
  def hash(self):
    s = utils.to_json(self.toJSONDict())
    return utils.hash_b64(s)

  def process_value_in(self, field_name, field_value):
    """
    process some fields on the way into the object
    """
    if field_value == None:
      return None

    val = self._process_value_in(field_name, field_value)
    if val != None:
      return val
    else:
      return field_value

  def _process_value_in(self, field_name, field_value):
    return None

  def process_value_out(self, field_name, field_value):
    """
    process some fields on the way out of the object
    """
    if field_value == None:
      return None

    val = self._process_value_out(field_name, field_value)
    if val != None:
      return val
    else:
      return field_value

  def _process_value_out(self, field_name, field_value):
    return None

  def __eq__(self, other):
    if not hasattr(self, 'uuid'):
      return super(HeliosObject,self) == other

    return other != None and self.uuid == other.uuid

class EncryptedAnswer(HeliosObject):
  """
  An encrypted answer to a single election question
  """

  FIELDS = ['choices', 'individual_proofs', 'overall_proof', 'randomness', 'answer']

  # FIXME: remove this constructor and use only named-var constructor from HeliosObject
  def __init__(self, choices=None, individual_proofs=None, overall_proof=None, randomness=None, answer=None):
    self.choices = choices
    self.individual_proofs = individual_proofs
    self.overall_proof = overall_proof
    self.randomness = randomness
    self.answer = answer

  @classmethod
  def generate_plaintexts(cls, pk, min=0, max=1):
    plaintexts = []
    running_product = 1

    # run the product up to the min
    for i in range(max+1):
      # if we're in the range, add it to the array
      if i >= min:
        plaintexts.append(algs.EGPlaintext(running_product, pk))

      # next value in running product
      running_product = (running_product * pk.g) % pk.p

    return plaintexts

  def verify_plaintexts_and_randomness(self, pk):
    """
    this applies only if the explicit answers and randomness factors are given
    we do not verify the proofs here, that is the verify() method
    """
    if not hasattr(self, 'answer'):
      return False

    for choice_num in range(len(self.choices)):
      choice = self.choices[choice_num]
      choice.pk = pk

      # redo the encryption
      # WORK HERE (paste from below encryption)

    return False

  def verify(self, pk, min=0, max=1):
    possible_plaintexts = self.generate_plaintexts(pk)
    homomorphic_sum = 0

    for choice_num in range(len(self.choices)):
      choice = self.choices[choice_num]
      choice.pk = pk
      individual_proof = self.individual_proofs[choice_num]

      # verify that elements belong to the proper group
      if not choice.check_group_membership(pk):
        return False

      # verify the proof on the encryption of that choice
      if not choice.verify_disjunctive_encryption_proof(possible_plaintexts, individual_proof, algs.EG_disjunctive_challenge_generator):
        return False

      # compute homomorphic sum if needed
      if max != None:
        homomorphic_sum = choice * homomorphic_sum

    if max != None:
      # determine possible plaintexts for the sum
      sum_possible_plaintexts = self.generate_plaintexts(pk, min=min, max=max)

      # verify the sum
      return homomorphic_sum.verify_disjunctive_encryption_proof(sum_possible_plaintexts, self.overall_proof, algs.EG_disjunctive_challenge_generator)
    else:
      # approval voting, no need for overall proof verification
      return True

  def toJSONDict(self, with_randomness=False):
    value = {
      'choices': [c.to_dict() for c in self.choices],
      'individual_proofs' : [p.to_dict() for p in self.individual_proofs]
    }

    if self.overall_proof:
      value['overall_proof'] = self.overall_proof.to_dict()
    else:
      value['overall_proof'] = None

    if with_randomness:
      value['randomness'] = [str(r) for r in self.randomness]
      value['answer'] = self.answer

    return value

  @classmethod
  def fromJSONDict(cls, d, pk=None):
    ea = cls()

    ea.choices = [algs.EGCiphertext.from_dict(c, pk) for c in d['choices']]
    ea.individual_proofs = [algs.EGZKDisjunctiveProof.from_dict(p) for p in d['individual_proofs']]

    if d['overall_proof']:
      ea.overall_proof = algs.EGZKDisjunctiveProof.from_dict(d['overall_proof'])
    else:
      ea.overall_proof = None

    if d.has_key('randomness'):
      ea.randomness = [int(r) for r in d['randomness']]
      ea.answer = d['answer']

    return ea

  @classmethod
  def fromElectionAndAnswer(cls, election, question_num, answer_indexes):
    """
    Given an election, a question number, and a list of answers to that question
    in the form of an array of 0-based indexes into the answer array,
    produce an EncryptedAnswer that works.
    """
    question = election.questions[question_num]
    answers = question['answers']
    pk = election.public_key

    # initialize choices, individual proofs, randomness and overall proof
    choices = [None for a in range(len(answers))]
    individual_proofs = [None for a in range(len(answers))]
    overall_proof = None
    randomness = [None for a in range(len(answers))]

    # possible plaintexts [0, 1]
    plaintexts = cls.generate_plaintexts(pk)

    # keep track of number of options selected.
    num_selected_answers = 0;

    # homomorphic sum of all
    homomorphic_sum = 0
    randomness_sum = 0

    # min and max for number of answers, useful later
    min_answers = 0
    if question.has_key('min'):
      min_answers = question['min']
    max_answers = question['max']

    # go through each possible answer and encrypt either a g^0 or a g^1.
    for answer_num in range(len(answers)):
      plaintext_index = 0

      # assuming a list of answers
      if answer_num in answer_indexes:
        plaintext_index = 1
        num_selected_answers += 1

      # randomness and encryption
      randomness[answer_num] = algs.Utils.random_mpz_lt(pk.q)
      choices[answer_num] = pk.encrypt_with_r(plaintexts[plaintext_index], randomness[answer_num])

      # generate proof
      individual_proofs[answer_num] = choices[answer_num].generate_disjunctive_encryption_proof(plaintexts, plaintext_index,
                                                randomness[answer_num], algs.EG_disjunctive_challenge_generator)

      # sum things up homomorphically if needed
      if max_answers != None:
        homomorphic_sum = choices[answer_num] * homomorphic_sum
        randomness_sum = (randomness_sum + randomness[answer_num]) % pk.q

    # prove that the sum is 0 or 1 (can be "blank vote" for this answer)
    # num_selected_answers is 0 or 1, which is the index into the plaintext that is actually encoded

    if num_selected_answers < min_answers:
      raise Exception("Need to select at least %s answer(s)" % min_answers)

    if max_answers != None:
      sum_plaintexts = cls.generate_plaintexts(pk, min=min_answers, max=max_answers)

      # need to subtract the min from the offset
      overall_proof = homomorphic_sum.generate_disjunctive_encryption_proof(sum_plaintexts, num_selected_answers - min_answers, randomness_sum, algs.EG_disjunctive_challenge_generator);
    else:
      # approval voting
      overall_proof = None

    return cls(choices, individual_proofs, overall_proof, randomness, answer_indexes)

class EncryptedVote(HeliosObject):
  """
  An encrypted ballot
  """
  FIELDS = ['encrypted_answers', 'election_hash', 'election_uuid']

  def verify(self, election):
    # right number of answers
    if len(self.encrypted_answers) != len(election.questions):
      return False

    # check hash
    if self.election_hash != election.hash:
      # print "%s / %s " % (self.election_hash, election.hash)
      return False

    # check ID
    if self.election_uuid != election.uuid:
      return False

    # check proofs on all of answers
    for question_num in range(len(election.questions)):
      ea = self.encrypted_answers[question_num]

      question = election.questions[question_num]
      min_answers = 0
      if question.has_key('min'):
        min_answers = question['min']

      if not ea.verify(election.public_key, min=min_answers, max=question['max']):
        return False

    return True

  def get_hash(self):
    return utils.hash_b64(utils.to_json(self.toJSONDict()))

  def toJSONDict(self, with_randomness=False):
    return {
      'answers': [a.toJSONDict(with_randomness) for a in self.encrypted_answers],
      'election_hash': self.election_hash,
      'election_uuid': self.election_uuid
    }

  @classmethod
  def fromJSONDict(cls, d, pk=None):
    ev = cls()

    ev.encrypted_answers = [EncryptedAnswer.fromJSONDict(ea, pk) for ea in d['answers']]
    ev.election_hash = d['election_hash']
    ev.election_uuid = d['election_uuid']

    return ev

  @classmethod
  def fromElectionAndAnswers(cls, election, answers):
    pk = election.public_key

    # each answer is an index into the answer array
    encrypted_answers = [EncryptedAnswer.fromElectionAndAnswer(election, answer_num, answers[answer_num]) for answer_num in range(len(answers))]
    return cls(encrypted_answers=encrypted_answers, election_hash=election.hash, election_uuid = election.uuid)


def one_question_winner(question, result, num_cast_votes):
  """
  determining the winner for one question
  """
  # sort the answers , keep track of the index
  counts = sorted(enumerate(result), key=lambda(x): x[1])
  counts.reverse()

  # if there's a max > 1, we assume that the top MAX win
  if question['max'] > 1:
    return [c[0] for c in counts[:question['max']]]

  # if max = 1, then depends on absolute or relative
  if question['result_type'] == 'absolute':
    if counts[0][1] >=  (num_cast_votes/2 + 1):
      return [counts[0][0]]
    else:
      return []

  if question['result_type'] == 'relative':
    return [counts[0][0]]

class Election(HeliosObject):

  FIELDS = ['uuid', 'questions', 'name', 'short_name', 'description', 'voters_hash', 'openreg',
      'frozen_at', 'public_key', 'private_key', 'cast_url', 'result', 'result_proof', 'use_voter_aliases', 'voting_starts_at', 'voting_ends_at', 'election_type']

  JSON_FIELDS = ['uuid', 'questions', 'name', 'short_name', 'description', 'voters_hash', 'openreg',
      'frozen_at', 'public_key', 'cast_url', 'use_voter_aliases', 'voting_starts_at', 'voting_ends_at']

  # need to add in v3.1: use_advanced_audit_features, election_type, and probably more

  def init_tally(self):
    return Tally(election=self)

  def _process_value_in(self, field_name, field_value):
    if field_name == 'frozen_at' or field_name == 'voting_starts_at' or field_name == 'voting_ends_at':
      if type(field_value) == str or type(field_value) == unicode:
        return datetime.datetime.strptime(field_value, '%Y-%m-%d %H:%M:%S')

    if field_name == 'public_key':
      return algs.EGPublicKey.fromJSONDict(field_value)

    if field_name == 'private_key':
      return algs.EGSecretKey.fromJSONDict(field_value)

  def _process_value_out(self, field_name, field_value):
    # the date
    if field_name == 'frozen_at' or field_name == 'voting_starts_at' or field_name == 'voting_ends_at':
      return str(field_value)

    if field_name == 'public_key' or field_name == 'private_key':
      return field_value.toJSONDict()

  @property
  def registration_status_pretty(self):
    if self.openreg:
      return "Open"
    else:
      return "Closed"

  @property
  def winners(self):
    """
    Depending on the type of each question, determine the winners
    returns an array of winners for each question, aka an array of arrays.
    assumes that if there is a max to the question, that's how many winners there are.
    """
    return [one_question_winner(self.questions[i], self.result[i], self.num_cast_votes) for i in range(len(self.questions))]

  @property
  def pretty_result(self):
    if not self.result:
      return None

    # get the winners
    winners = self.winners

    raw_result = self.result
    prettified_result = []

    # loop through questions
    for i in range(len(self.questions)):
      q = self.questions[i]
      pretty_question = []

      # go through answers
      for j in range(len(q['answers'])):
        a = q['answers'][j]
        count = raw_result[i][j]
        pretty_question.append({'answer': a, 'count': count, 'winner': (j in winners[i])})

      prettified_result.append({'question': q['short_name'], 'answers': pretty_question})

    return prettified_result


class Voter(HeliosObject):
  """
  A voter in an election
  """
  FIELDS = ['election_uuid', 'uuid', 'voter_type', 'voter_id', 'name', 'alias']
  JSON_FIELDS = ['election_uuid', 'uuid', 'voter_type', 'voter_id_hash', 'name']

  # alternative, for when the voter is aliased
  ALIASED_VOTER_JSON_FIELDS = ['election_uuid', 'uuid', 'alias']

  def toJSONDict(self):
    fields = None
    if self.alias != None:
      return super(Voter, self).toJSONDict(self.ALIASED_VOTER_JSON_FIELDS)
    else:
      return super(Voter,self).toJSONDict()

  @property
  def voter_id_hash(self):
    if self.voter_login_id:
      # for backwards compatibility with v3.0, and since it doesn't matter
      # too much if we hash the email or the unique login ID here.
      return utils.hash_b64(self.voter_login_id)
    else:
      return utils.hash_b64(self.voter_id)

class Trustee(HeliosObject):
  """
  a trustee
  """
  FIELDS = ['uuid', 'public_key', 'public_key_hash', 'pok', 'decryption_factors', 'decryption_proofs', 'email']

  def _process_value_in(self, field_name, field_value):
    if field_name == 'public_key':
      return algs.EGPublicKey.fromJSONDict(field_value)

    if field_name == 'pok':
      return algs.DLogProof.fromJSONDict(field_value)

  def _process_value_out(self, field_name, field_value):
    if field_name == 'public_key' or field_name == 'pok':
      return field_value.toJSONDict()

class CastVote(HeliosObject):
  """
  A cast vote, which includes an encrypted vote and some cast metadata
  """
  FIELDS = ['vote', 'cast_at', 'voter_uuid', 'voter_hash', 'vote_hash']

  def __init__(self, *args, **kwargs):
    super(CastVote, self).__init__(*args, **kwargs)
    self.election = None

  @classmethod
  def fromJSONDict(cls, d, election=None):
    o = cls()
    o.election = election
    o.set_from_args(**d)
    return o

  def toJSONDict(self, include_vote=True):
    result = super(CastVote,self).toJSONDict()
    if not include_vote:
      del result['vote']
    return result

  @classmethod
  def fromOtherObject(cls, o, election):
    obj = cls()
    obj.election = election
    obj.set_from_other_object(o)
    return obj

  def _process_value_in(self, field_name, field_value):
    if field_name == 'cast_at':
      if type(field_value) == str:
        return datetime.datetime.strptime(field_value, '%Y-%m-%d %H:%M:%S')

    if field_name == 'vote':
      return EncryptedVote.fromJSONDict(field_value, self.election.public_key)

  def _process_value_out(self, field_name, field_value):
    # the date
    if field_name == 'cast_at':
      return str(field_value)

    if field_name == 'vote':
      return field_value.toJSONDict()

  def issues(self, election):
    """
    Look for consistency problems
    """
    issues = []

    # check the election
    if self.vote.election_uuid != election.uuid:
      issues.append("the vote's election UUID does not match the election for which this vote is being cast")

    return issues

class DLogTable(object):
  """
  Keeping track of discrete logs
  """

  def __init__(self, base, modulus):
    self.dlogs = {}
    self.dlogs[1] = 0
    self.last_dlog_result = 1
    self.counter = 0

    self.base = base
    self.modulus = modulus

  def increment(self):
    self.counter += 1

    # new value
    new_value = (self.last_dlog_result * self.base) % self.modulus

    # record the discrete log
    self.dlogs[new_value] = self.counter

    # record the last value
    self.last_dlog_result = new_value

  def precompute(self, up_to):
    while self.counter < up_to:
      self.increment()

  def lookup(self, value):
    return self.dlogs.get(value, None)


class Tally(HeliosObject):
  """
  A running homomorphic tally
  """

  FIELDS = ['num_tallied', 'tally']
  JSON_FIELDS = ['num_tallied', 'tally']

  def __init__(self, *args, **kwargs):
    super(Tally, self).__init__(*args, **kwargs)

    self.election = kwargs.get('election',None)

    if self.election:
      self.init_election(self.election)
    else:
      self.questions = None
      self.public_key = None

      if not self.tally:
        self.tally = None

    # initialize
    if self.num_tallied == None:
      self.num_tallied = 0

  def init_election(self, election):
    """
    given the election, initialize some params
    """
    self.questions = election.questions
    self.public_key = election.public_key

    if not self.tally:
      self.tally = [[0 for a in q['answers']] for q in self.questions]

  def add_vote_batch(self, encrypted_votes, verify_p=True):
    """
    Add a batch of votes. Eventually, this will be optimized to do an aggregate proof verification
    rather than a whole proof verif for each vote.
    """
    for vote in encrypted_votes:
      self.add_vote(vote, verify_p)

  def add_vote(self, encrypted_vote, verify_p=True):
    # do we verify?
    if verify_p:
      if not encrypted_vote.verify(self.election):
        raise Exception('Bad Vote')

    # for each question
    for question_num in range(len(self.questions)):
      question = self.questions[question_num]
      answers = question['answers']

      # for each possible answer to each question
      for answer_num in range(len(answers)):
        # do the homomorphic addition into the tally
        enc_vote_choice = encrypted_vote.encrypted_answers[question_num].choices[answer_num]
        enc_vote_choice.pk = self.public_key
        self.tally[question_num][answer_num] = encrypted_vote.encrypted_answers[question_num].choices[answer_num] * self.tally[question_num][answer_num]

    self.num_tallied += 1

  def decryption_factors_and_proofs(self, sk):
    """
    returns an array of decryption factors and a corresponding array of decryption proofs.
    makes the decryption factors into strings, for general Helios / JS compatibility.
    """
    # for all choices of all questions (double list comprehension)
    decryption_factors = []
    decryption_proof = []

    for question_num, question in enumerate(self.questions):
      answers = question['answers']
      question_factors = []
      question_proof = []

      for answer_num, answer in enumerate(answers):
        # do decryption and proof of it
        dec_factor, proof = sk.decryption_factor_and_proof(self.tally[question_num][answer_num])

        # look up appropriate discrete log
        # this is the string conversion
        question_factors.append(str(dec_factor))
        question_proof.append(proof.toJSONDict())

      decryption_factors.append(question_factors)
      decryption_proof.append(question_proof)

    return decryption_factors, decryption_proof

  def decrypt_and_prove(self, sk, discrete_logs=None):
    """
    returns an array of tallies and a corresponding array of decryption proofs.
    """

    # who's keeping track of discrete logs?
    if not discrete_logs:
      discrete_logs = self.discrete_logs

    # for all choices of all questions (double list comprehension)
    decrypted_tally = []
    decryption_proof = []

    for question_num in range(len(self.questions)):
      question = self.questions[question_num]
      answers = question['answers']
      question_tally = []
      question_proof = []

      for answer_num in range(len(answers)):
        # do decryption and proof of it
        plaintext, proof = sk.prove_decryption(self.tally[question_num][answer_num])

        # look up appropriate discrete log
        question_tally.append(discrete_logs[plaintext])
        question_proof.append(proof)

      decrypted_tally.append(question_tally)
      decryption_proof.append(question_proof)

    return decrypted_tally, decryption_proof

  def verify_decryption_proofs(self, decryption_factors, decryption_proofs, public_key, challenge_generator):
    """
    decryption_factors is a list of lists of dec factors
    decryption_proofs are the corresponding proofs
    public_key is, of course, the public key of the trustee
    """

    # go through each one
    for q_num, q in enumerate(self.tally):
      for a_num, answer_tally in enumerate(q):
        # parse the proof
        proof = algs.EGZKProof.fromJSONDict(decryption_proofs[q_num][a_num])

        # check that g, alpha, y, dec_factor is a DH tuple
        if not proof.verify(public_key.g, answer_tally.alpha, public_key.y, int(decryption_factors[q_num][a_num]), public_key.p, public_key.q, challenge_generator):
          return False

    return True

  def decrypt_from_factors(self, decryption_factors, public_key):
    """
    decrypt a tally given decryption factors

    The decryption factors are a list of decryption factor sets, for each trustee.
    Each decryption factor set is a list of lists of decryption factors (questions/answers).
    """

    # pre-compute a dlog table
    dlog_table = DLogTable(base = public_key.g, modulus = public_key.p)
    dlog_table.precompute(self.num_tallied)

    result = []

    # go through each one
    for q_num, q in enumerate(self.tally):
      q_result = []

      for a_num, a in enumerate(q):
        # coalesce the decryption factors into one list
        dec_factor_list = [df[q_num][a_num] for df in decryption_factors]
        raw_value = self.tally[q_num][a_num].decrypt(dec_factor_list, public_key)

        q_result.append(dlog_table.lookup(raw_value))

      result.append(q_result)

    return result

  def _process_value_in(self, field_name, field_value):
    if field_name == 'tally':
      return [[algs.EGCiphertext.fromJSONDict(a) for a in q] for q in field_value]

  def _process_value_out(self, field_name, field_value):
    if field_name == 'tally':
      return [[a.toJSONDict() for a in q] for q in field_value]
