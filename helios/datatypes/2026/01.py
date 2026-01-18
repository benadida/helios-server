"""
Datatypes for 2026/01 Helios - Enhanced NIZK proofs with context binding

This module defines datatype classes that use SHA-256 context-bound proofs.
Elections with this datatype bind proofs to election_hash, question_index,
answer_index, and voter_alias, preventing proof transplantation attacks.

Key differences from legacy/2011/01:
- Uses SHA-256 instead of SHA-1 for challenge generation
- Includes context binding in proof verification
- Proofs are bound to specific election/question/answer/voter
"""

from helios.datatypes import LDObject, arrayOf, DictObject, ListObject
from helios.crypto import elgamal as crypto_elgamal
from helios.workflows import homomorphic
from helios import models


class Election(LDObject):
    """
    Election datatype for 2026/01 with enhanced audit features.
    """
    WRAPPED_OBJ_CLASS = models.Election
    FIELDS = ['uuid', 'questions', 'name', 'short_name', 'description',
              'voters_hash', 'openreg', 'frozen_at', 'public_key', 'cast_url',
              'use_advanced_audit_features', 'use_voter_aliases',
              'voting_starts_at', 'voting_ends_at']

    STRUCTURED_FIELDS = {
        'public_key': 'pkc/elgamal/PublicKey',
        'voting_starts_at': 'core/Timestamp',
        'voting_ends_at': 'core/Timestamp',
        'frozen_at': 'core/Timestamp',
        'questions': '2026/01/Questions',
    }


class Voter(LDObject):
    """
    Voter datatype with alias support for context binding.
    """
    WRAPPED_OBJ_CLASS = models.Voter
    FIELDS = ['election_uuid', 'uuid', 'voter_type', 'voter_id_hash', 'name']
    ALIASED_VOTER_FIELDS = ['election_uuid', 'uuid', 'alias']

    def toDict(self, complete=False):
        """
        Depending on whether the voter is aliased, use different fields.
        The alias is important for context binding in proofs.
        """
        if self.wrapped_obj.alias is not None:
            return super(Voter, self).toDict(self.ALIASED_VOTER_FIELDS, complete=complete)
        return super(Voter, self).toDict(complete=complete)


class EncryptedAnswer(LDObject):
    """
    Encrypted answer with SHA-256 context-bound proofs.

    The proofs in this datatype use SHA-256 challenge generation with
    context binding to election_hash, question_index, and answer_index.
    """
    WRAPPED_OBJ_CLASS = homomorphic.EncryptedAnswer
    FIELDS = ['choices', 'individual_proofs', 'overall_proof']
    STRUCTURED_FIELDS = {
        'choices': arrayOf('pkc/elgamal/EGCiphertext'),
        'individual_proofs': arrayOf('2026/01/EGZKDisjunctiveProof'),
        'overall_proof': '2026/01/EGZKDisjunctiveProof'
    }


class EncryptedAnswerWithRandomness(LDObject):
    """
    Encrypted answer with randomness for audit purposes.
    """
    FIELDS = ['choices', 'individual_proofs', 'overall_proof', 'randomness', 'answer']
    STRUCTURED_FIELDS = {
        'choices': arrayOf('pkc/elgamal/EGCiphertext'),
        'individual_proofs': arrayOf('2026/01/EGZKDisjunctiveProof'),
        'overall_proof': '2026/01/EGZKDisjunctiveProof',
        'randomness': arrayOf('core/BigInteger')
    }


class EncryptedVote(LDObject):
    """
    An encrypted ballot with SHA-256 context-bound proofs.
    """
    WRAPPED_OBJ_CLASS = homomorphic.EncryptedVote
    FIELDS = ['answers', 'election_hash', 'election_uuid']
    STRUCTURED_FIELDS = {
        'answers': arrayOf('2026/01/EncryptedAnswer')
    }

    def includeRandomness(self):
        return self.instantiate(self.wrapped_obj, datatype='2026/01/EncryptedVoteWithRandomness')


class EncryptedVoteWithRandomness(LDObject):
    """
    An encrypted ballot with randomness for audit purposes.
    """
    WRAPPED_OBJ_CLASS = homomorphic.EncryptedVote
    FIELDS = ['answers', 'election_hash', 'election_uuid']
    STRUCTURED_FIELDS = {
        'answers': arrayOf('2026/01/EncryptedAnswerWithRandomness')
    }


class EGZKProofCommitment(DictObject, LDObject):
    """
    Commitment component of a ZK proof.
    """
    FIELDS = ['A', 'B']
    STRUCTURED_FIELDS = {
        'A': 'core/BigInteger',
        'B': 'core/BigInteger'
    }


class EGZKProof(LDObject):
    """
    Zero-knowledge proof with SHA-256 challenge generation.

    This proof type is verified using SHA-256 challenge generation
    with context binding when used in 2026/01 elections.
    """
    WRAPPED_OBJ_CLASS = crypto_elgamal.ZKProof
    FIELDS = ['commitment', 'challenge', 'response']
    STRUCTURED_FIELDS = {
        'commitment': '2026/01/EGZKProofCommitment',
        'challenge': 'core/BigInteger',
        'response': 'core/BigInteger'
    }


class EGZKDisjunctiveProof(LDObject):
    """
    Disjunctive zero-knowledge proof with SHA-256 challenge generation.

    Used to prove that an encrypted value is one of a set of possible
    plaintexts without revealing which one.
    """
    WRAPPED_OBJ_CLASS = crypto_elgamal.ZKDisjunctiveProof
    FIELDS = ['proofs']
    STRUCTURED_FIELDS = {
        'proofs': arrayOf('2026/01/EGZKProof')
    }

    def loadDataFromDict(self, d):
        """Ensure proofs array is properly structured."""
        return super(EGZKDisjunctiveProof, self).loadDataFromDict({'proofs': d})

    def toDict(self, complete=False):
        """Return proofs array directly for compatibility."""
        return super(EGZKDisjunctiveProof, self).toDict(complete=complete)['proofs']


class Questions(ListObject, LDObject):
    """List of election questions."""
    WRAPPED_OBJ = list


class ShortCastVote(LDObject):
    """Short form of cast vote for listings."""
    FIELDS = ['cast_at', 'voter_uuid', 'voter_hash', 'vote_hash']
    STRUCTURED_FIELDS = {'cast_at': 'core/Timestamp'}


class CastVote(LDObject):
    """
    A cast vote record with full vote data.
    """
    FIELDS = ['vote', 'cast_at', 'voter_uuid', 'voter_hash', 'vote_hash']
    STRUCTURED_FIELDS = {
        'cast_at': 'core/Timestamp',
        'vote': '2026/01/EncryptedVote'
    }

    @property
    def short(self):
        return self.instantiate(self.wrapped_obj, datatype='2026/01/ShortCastVote')


class Trustee(LDObject):
    """
    Trustee with SHA-256 proofs for decryption.
    """
    WRAPPED_OBJ_CLASS = models.Trustee
    FIELDS = ['uuid', 'public_key', 'public_key_hash', 'pok',
              'decryption_factors', 'decryption_proofs', 'email']
    STRUCTURED_FIELDS = {
        'pok': 'pkc/elgamal/DiscreteLogProof',
        'public_key': 'pkc/elgamal/PublicKey',
        'decryption_factors': arrayOf(arrayOf('core/BigInteger')),
        'decryption_proofs': arrayOf(arrayOf('2026/01/EGZKProof'))
    }


class EGParams(LDObject):
    """ElGamal cryptosystem parameters."""
    WRAPPED_OBJ_CLASS = crypto_elgamal.Cryptosystem
    FIELDS = ['p', 'q', 'g']
    STRUCTURED_FIELDS = {
        'p': 'core/BigInteger',
        'q': 'core/BigInteger',
        'g': 'core/BigInteger'
    }


class EGPublicKey(LDObject):
    """ElGamal public key."""
    WRAPPED_OBJ_CLASS = crypto_elgamal.PublicKey
    FIELDS = ['y', 'p', 'g', 'q']
    STRUCTURED_FIELDS = {
        'y': 'core/BigInteger',
        'p': 'core/BigInteger',
        'q': 'core/BigInteger',
        'g': 'core/BigInteger'
    }


class EGSecretKey(LDObject):
    """ElGamal secret key."""
    WRAPPED_OBJ_CLASS = crypto_elgamal.SecretKey
    FIELDS = ['x', 'public_key']
    STRUCTURED_FIELDS = {
        'x': 'core/BigInteger',
        'public_key': '2026/01/EGPublicKey'
    }


class EGCiphertext(LDObject):
    """ElGamal ciphertext."""
    WRAPPED_OBJ_CLASS = crypto_elgamal.Ciphertext
    FIELDS = ['alpha', 'beta']
    STRUCTURED_FIELDS = {
        'alpha': 'core/BigInteger',
        'beta': 'core/BigInteger'
    }


class DLogProof(LDObject):
    """Discrete log proof with SHA-256 challenge."""
    WRAPPED_OBJ_CLASS = crypto_elgamal.DLogProof
    FIELDS = ['commitment', 'challenge', 'response']
    STRUCTURED_FIELDS = {
        'commitment': 'core/BigInteger',
        'challenge': 'core/BigInteger',
        'response': 'core/BigInteger'
    }

    def __init__(self, wrapped_obj):
        if isinstance(wrapped_obj, dict):
            raise Exception("DLogProof cannot be initialized with dict")
        super(DLogProof, self).__init__(wrapped_obj)


class Result(LDObject):
    """Election result."""
    WRAPPED_OBJ = list

    def loadDataFromDict(self, d):
        self.wrapped_obj = d

    def toDict(self, complete=False):
        return self.wrapped_obj


class Tally(LDObject):
    """Encrypted tally."""
    WRAPPED_OBJ_CLASS = homomorphic.Tally
    FIELDS = ['tally', 'num_tallied']
    STRUCTURED_FIELDS = {
        'tally': arrayOf(arrayOf('pkc/elgamal/EGCiphertext'))
    }


class Eligibility(ListObject, LDObject):
    """Voter eligibility rules."""
    WRAPPED_OBJ = list
