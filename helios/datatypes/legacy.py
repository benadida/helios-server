"""
Legacy datatypes for Helios (v3.0)
"""

from helios.datatypes import LDObject, arrayOf, DictObject, ListObject
from helios.crypto import elgamal as crypto_elgamal
from helios.workflows import homomorphic
from helios import models

##
##

class LegacyObject(LDObject):
    WRAPPED_OBJ_CLASS = dict
    USE_JSON_LD = False

class Election(LegacyObject):
    WRAPPED_OBJ_CLASS = models.Election
    FIELDS = ['uuid', 'questions', 'name', 'short_name', 'description', 'voters_hash', 'openreg',
              'frozen_at', 'public_key', 'cast_url', 'use_voter_aliases', 'voting_starts_at', 'voting_ends_at']

    STRUCTURED_FIELDS = {
        'public_key' : 'legacy/EGPublicKey',
        'voting_starts_at': 'core/Timestamp',
        'voting_ends_at': 'core/Timestamp',
        'frozen_at': 'core/Timestamp'
        }

class EncryptedAnswer(LegacyObject):
    WRAPPED_OBJ_CLASS = homomorphic.EncryptedAnswer
    FIELDS = ['choices', 'individual_proofs', 'overall_proof']
    STRUCTURED_FIELDS = {
        'choices': arrayOf('legacy/EGCiphertext'),
        'individual_proofs': arrayOf('legacy/EGZKDisjunctiveProof'),
        'overall_proof' : 'legacy/EGZKDisjunctiveProof'
        }

class EncryptedAnswerWithRandomness(LegacyObject):
    FIELDS = ['choices', 'individual_proofs', 'overall_proof', 'randomness', 'answer']
    STRUCTURED_FIELDS = {
        'choices': arrayOf('legacy/EGCiphertext'),
        'individual_proofs': arrayOf('legacy/EGZKDisjunctiveProof'),
        'overall_proof' : 'legacy/EGZKDisjunctiveProof',
        'randomness' : arrayOf('core/BigInteger')
        }

class EncryptedVote(LegacyObject):
    """
    An encrypted ballot
    """
    WRAPPED_OBJ_CLASS = homomorphic.EncryptedVote
    FIELDS = ['answers', 'election_hash', 'election_uuid']
    STRUCTURED_FIELDS = {
        'answers' : arrayOf('legacy/EncryptedAnswer')
        }

    def includeRandomness(self):
        return self.instantiate(self.wrapped_obj, datatype='legacy/EncryptedVoteWithRandomness')

class EncryptedVoteWithRandomness(LegacyObject):
    """
    An encrypted ballot with randomness for answers
    """
    WRAPPED_OBJ_CLASS = homomorphic.EncryptedVote
    FIELDS = ['answers', 'election_hash', 'election_uuid']
    STRUCTURED_FIELDS = {
        'answers' : arrayOf('legacy/EncryptedAnswerWithRandomness')
        }
    

class Voter(LegacyObject):
    FIELDS = ['election_uuid', 'uuid', 'voter_type', 'voter_id_hash', 'name']

    ALIASED_VOTER_FIELDS = ['election_uuid', 'uuid', 'alias']

    def toDict(self, complete=False):
        """
        depending on whether the voter is aliased, use different fields
        """
        if self.wrapped_obj.alias is not None:
            return super(Voter, self).toDict(self.ALIASED_VOTER_FIELDS, complete = complete)
        else:
            return super(Voter,self).toDict(complete = complete)


class ShortCastVote(LegacyObject):
    FIELDS = ['cast_at', 'voter_uuid', 'voter_hash', 'vote_hash']
    STRUCTURED_FIELDS = {'cast_at' : 'core/Timestamp'}

class CastVote(LegacyObject):
    FIELDS = ['vote', 'cast_at', 'voter_uuid', 'voter_hash', 'vote_hash']
    STRUCTURED_FIELDS = {
        'cast_at' : 'core/Timestamp',
        'vote' : 'legacy/EncryptedVote'}

    @property
    def short(self):
        return self.instantiate(self.wrapped_obj, datatype='legacy/ShortCastVote')

class Trustee(LegacyObject):
    FIELDS = ['uuid', 'public_key', 'public_key_hash', 'pok', 'decryption_factors', 'decryption_proofs', 'email']

    STRUCTURED_FIELDS = {
        'public_key' : 'legacy/EGPublicKey',
        'pok': 'legacy/DLogProof',
        'decryption_factors': arrayOf(arrayOf('core/BigInteger')),
        'decryption_proofs' : arrayOf(arrayOf('legacy/EGZKProof'))}

class EGParams(LegacyObject):
    WRAPPED_OBJ_CLASS = crypto_elgamal.Cryptosystem
    FIELDS = ['p', 'q', 'g']
    STRUCTURED_FIELDS = {
        'p': 'core/BigInteger',
        'q': 'core/BigInteger',
        'g': 'core/BigInteger'}

class EGPublicKey(LegacyObject):
    WRAPPED_OBJ_CLASS = crypto_elgamal.PublicKey
    FIELDS = ['y', 'p', 'g', 'q']
    STRUCTURED_FIELDS = {
        'y': 'core/BigInteger',
        'p': 'core/BigInteger',
        'q': 'core/BigInteger',
        'g': 'core/BigInteger'}

class EGSecretKey(LegacyObject):
    WRAPPED_OBJ_CLASS = crypto_elgamal.SecretKey
    FIELDS = ['x','public_key']
    STRUCTURED_FIELDS = {
        'x': 'core/BigInteger',
        'public_key': 'legacy/EGPublicKey'}

class EGCiphertext(LegacyObject):
    WRAPPED_OBJ_CLASS = crypto_elgamal.Ciphertext
    FIELDS = ['alpha','beta']
    STRUCTURED_FIELDS = {
        'alpha': 'core/BigInteger',
        'beta' : 'core/BigInteger'}

class EGZKProofCommitment(DictObject, LegacyObject):
    FIELDS = ['A', 'B']
    STRUCTURED_FIELDS = {
        'A' : 'core/BigInteger',
        'B' : 'core/BigInteger'}

    
class EGZKProof(LegacyObject):
    WRAPPED_OBJ_CLASS = crypto_elgamal.ZKProof
    FIELDS = ['commitment', 'challenge', 'response']
    STRUCTURED_FIELDS = {
        'commitment': 'legacy/EGZKProofCommitment',
        'challenge' : 'core/BigInteger',
        'response' : 'core/BigInteger'}
        
class EGZKDisjunctiveProof(LegacyObject):
    WRAPPED_OBJ_CLASS = crypto_elgamal.ZKDisjunctiveProof
    FIELDS = ['proofs']
    STRUCTURED_FIELDS = {
        'proofs': arrayOf('legacy/EGZKProof')}

    def loadDataFromDict(self, d):
        "hijack and make sure we add the proofs name back on"
        return super(EGZKDisjunctiveProof, self).loadDataFromDict({'proofs': d})

    def toDict(self, complete = False):
        "hijack toDict and make it return the proofs array only, since that's the spec for legacy"
        return super(EGZKDisjunctiveProof, self).toDict(complete=complete)['proofs']

class DLogProof(LegacyObject):
    WRAPPED_OBJ_CLASS = crypto_elgamal.DLogProof
    FIELDS = ['commitment', 'challenge', 'response']
    STRUCTURED_FIELDS = {
        'commitment' : 'core/BigInteger',
        'challenge' : 'core/BigInteger',
        'response' : 'core/BigInteger'}

    def __init__(self, wrapped_obj):
        if isinstance(wrapped_obj, dict):
            raise Exception("problem with dict")

        super(DLogProof,self).__init__(wrapped_obj)

class Result(LegacyObject):
    WRAPPED_OBJ = list

    def loadDataFromDict(self, d):
        self.wrapped_obj = d

    def toDict(self, complete=False):
        return self.wrapped_obj

class Questions(ListObject, LegacyObject):
    WRAPPED_OBJ = list

class Tally(LegacyObject):
    WRAPPED_OBJ_CLASS = homomorphic.Tally
    FIELDS = ['tally', 'num_tallied']
    STRUCTURED_FIELDS = {
        'tally': arrayOf(arrayOf('legacy/EGCiphertext'))}

class Eligibility(ListObject, LegacyObject):
    WRAPPED_OBJ = list
