from helios.workflows.homomorphic import Tally as HomomorphicTally
from helios.crypto.elgamal import Plaintext, Ciphertext
from helios.crypto import algs

# we are extending homomorphic workflow
from helios.workflows.homomorphic import *

from phoebus import phoebus

import random
import copy

TYPE = 'mixnet'

class ShuffleProof(WorkflowObject):
  @property
  def datatype(self):
    return "legacy/ShuffleProof"

class Mixnet(WorkflowObject):

  def __init__(self, election, *args, **kwargs):
    self.election = election
    super(Mixnet, self).__init__(*args, **kwargs)

  def mix(self, election, votes, verify=True, question_num=0):
    encrypted_ballots = []
    for index, vote in enumerate(votes):
      encrypted_ballots.append(vote.to_phoebus_ballot(election, question_num))

    ph_election = phoebus.Election.from_helios_election_model(self.election,
          encrypted_ballots=encrypted_ballots)

    new_ballots, mix_proof = ph_election.mix_ballots()
    new_votes = []

    new_answers = MixedAnswers([], question_num=0)
    for index, ballot in enumerate(new_ballots):
      cipher = Ciphertext(alpha=ballot.encrypted_ballot['a'],
          beta=ballot.encrypted_ballot['b'])
      new_answers.answers.append(MixedAnswer(choice=cipher, index=index))

    return new_answers, mix_proof


class MixedAnswers(WorkflowObject):

    @property
    def datatype(self):
        return "phoebus/MixedAnswers"

    def __init__(self, answers=[], question_num=0):
        self.answers = answers
        self.question_num = question_num

class MixedAnswer(WorkflowObject):

    @property
    def datatype(self):
        return "phoebus/MixedAnswer"

    def __init__(self, choice=None, index=None):
        self.index = index
        self.choice = choice

    @classmethod
    def fromEncryptedAnswer(cls, answer, index):
        return cls(answer=answer.choice, index=index)

    def to_phoebus_ballot(self, election, question_num):
      phoebus_enc = {'a': self.choice.alpha, 'b': self.choice.beta}
      question = election.questions[question_num]
      nr_candidates = len(question['answers'])
      max_choices = nr_candidates

      ballot = phoebus.Ballot.from_dict(
            {'encrypted_ballot': phoebus_enc,
              'nr_candidates': nr_candidates,
              'max_choices': max_choices,
              'public_key': election.public_key
            })
      return ballot

class Tally(HomomorphicTally):

  @property
  def datatype(self):
    return "phoebus/Tally"

  def get_encrypted_votes(self):
    return filter(bool, [v.vote for v in self.election.voter_set.all()])

  def decryption_factors_and_proofs(self, sk):
    """
    returns an array of decryption factors and a corresponding array of decryption proofs.
    makes the decryption factors into strings, for general Helios / JS compatibility.
    """
    # for all choices of all questions (double list comprehension)
    decryption_factors = [[]]
    decryption_proof = [[]]

    for vote in self.tally[0]:
        dec_factor, proof = sk.decryption_factor_and_proof(vote)
        decryption_factors[0].append(dec_factor)
        decryption_proof[0].append(proof)

    return decryption_factors, decryption_proof

  def decrypt_from_factors(self, decryption_factors, public_key):
    """
    decrypt a tally given decryption factors

    The decryption factors are a list of decryption factor sets, for each trustee.
    Each decryption factor set is a list of lists of decryption factors (questions/answers).
    """

    from phoebus import phoebus as ph
    # pre-compute a dlog table
    dlog_table = DLogTable(base = public_key.g, modulus = public_key.p)

    if not self.num_tallied:
      self.num_tallied = len(self.tally[0])

    dlog_table.precompute(self.num_tallied)

    result = []

    # go through each one
    for q_num, q in enumerate(self.tally):
      q_result = []

      for a_num, a in enumerate(q):
        # coalesce the decryption factors into one list
        dec_factor_list = [df[q_num][a_num] for df in decryption_factors]
        raw_value = self.tally[q_num][a_num].decrypt(dec_factor_list, public_key)

        # q_decode
        if raw_value > public_key.q:
            raw_value = -raw_value % public_key.p
        raw_value = raw_value - 1
        q_result.append(raw_value)

      result.append(q_result)

    return result

class EncryptedVote(EncryptedVote):

  @property
  def datatype(self):
    return "phoebus/EncryptedVote"

  @classmethod
  def fromElectionAndCipher(cls, election, cipher):
    pk = election.public_key

    # each answer is an index into the answer array
    encrypted_answers = [EncryptedAnswer(choices=[cipher])]

    return_val = cls()
    return_val.encrypted_answers = encrypted_answers
    return_val.election_hash = election.hash
    return_val.election_uuid = election.uuid

    return return_val

  @classmethod
  def fromElectionAndAnswers(cls, election, answers):
    encrypted_answers = [EncryptedAnswer.fromElectionAndAnswer(election,
        answer_num, answers[answer_num]) for answer_num in range(len(answers))]

    return_val = cls()
    return_val.encrypted_answers = encrypted_answers
    return_val.election_hash = election.hash
    return_val.election_uuid = election.uuid

    return return_val

  @property
  def encrypted_answer(self):
    return self.encrypted_answers[0]

  def to_phoebus_ballot(self):
    # hardcoded 0 answers
    from helios.models import Election
    cipher = self.get_cipher()
    phoebus_enc = {'a': cipher.alpha, 'b': cipher.beta, 'proof':
        self.encrypted_answers[0].encryption_proof}
    election = Election.objects.get(uuid=self.election_uuid)
    question = election.questions[0]
    nr_candidates = len(question['answers'])
    max_choices = nr_candidates

    ballot = phoebus.Ballot.from_dict(
        {'encrypted_ballot': phoebus_enc,
          'nr_candidates': nr_candidates,
          'max_choices': max_choices,
          'public_key': election.public_key
        })
    return ballot


  def get_cipher(self):
    """
    For one vote there is one cipher.
    """
    return self.encrypted_answers[0].choices[0]


  def verify(self, election):
    # right number of answers
    if len(self.encrypted_answers) != 1:
      return False

    # check hash
    if self.election_hash != election.hash:
      # print "%s / %s " % (self.election_hash, election.hash)
      return False

    # check ID
    if self.election_uuid != election.uuid:
      return False

    if not self.encrypted_answers[0].verify(election.public_key):
      return False

    return True


class EncryptedAnswer(EncryptedAnswer):

  @property
  def datatype(self):
    return "phoebus/EncryptedAnswer"

  def __init__(self, choices=None, encryption_proof=None, randomness=None,
               answer=None):
    self.choices = choices
    self.randomness = randomness
    self.answer = answer
    self.encryption_proof = encryption_proof

  @classmethod
  def fromElectionAndAnswer(cls, election, question_num, answer):
    pk = election.public_key
    question = election.questions[question_num]

    # transform it to phoebus Ballot object
    ballot = phoebus.Ballot.from_dict({
        'answers': answer,
        'nr_candidates': len(question['answers']),
        'max_choices': len(question['answers']),
        'public_key': pk})

    randomness = algs.Utils.random_mpz_lt(pk.q)
    encrypted, random = ballot.encrypt()
    ciph = Ciphertext(alpha=encrypted['a'], beta=encrypted['b'])
    proof = encrypted['proof']
    return cls(choices=[ciph], encryption_proof=proof)

  @property
  def choice(self):
    return self.choices[0]

  def verify(self, pk):
    verified = phoebus.verify_encryption(pk.p, pk.g, self.choice.alpha,
            self.choice.beta, self.encryption_proof)
    return verified


"""
Mixnet API
"""
def tallied(election):
  return election.mixing_finished

def compute_tally(election):
  raise NotImplemented

def tally_hash(election):
  pass


def ready_for_decription(election):
  pass

def decrypt_tally(election, decryption_factors):
    tally = election.encrypted_tally
    tally.init_election(election)
    decrypted = tally.decrypt_from_factors(decryption_factors,
                                           election.public_key)
    return decrypted

def get_decryption_factors_and_proof(election, key):
    tally = election.encrypted_tally
    tally.init_election(election)
    return tally.decryption_factors_and_proofs(key)

#def verify_encryption_proof(election, trustee):
  #pass

