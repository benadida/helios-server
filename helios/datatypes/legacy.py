"""
Legacy datatypes for Helios (v3.0)
"""

from helios.datatypes import LDObject, arrayOf

##
## utilities

class DictObject(object):
    def __init__(self, d):
        self.d = d
        
    def __getattr__(self, k):
        return self.d[k]

##
##

class LegacyObject(LDObject):
    USE_JSON_LD = False

class Election(LegacyObject):
    FIELDS = ['uuid', 'questions', 'name', 'short_name', 'description', 'voters_hash', 'openreg',
              'frozen_at', 'public_key', 'cast_url', 'use_voter_aliases', 'voting_starts_at', 'voting_ends_at']

    STRUCTURED_FIELDS = {
        'public_key' : 'legacy/EGPublicKey',
        'voting_starts_at': 'core/Timestamp',
        'voting_ends_at': 'core/Timestamp',
        'frozen_at': 'core/Timestamp'
        }
        
class EncryptedAnswer(LegacyObject):
    FIELDS = ['choices', 'individual_proofs', 'overall_proof']
    STRUCTURED_FIELDS = {
        'choices': arrayOf('legacy/EGCiphertext'),
        'individual_proofs': arrayOf('legacy/EGZKDisjunctiveProof'),
        'overall_proof' : 'legacy/EGZKDisjunctiveProof'
        }

class EncryptedAnswerWithDecryption(LegacyObject):
    FIELDS = ['choices', 'individual_proofs', 'overall_proof', 'randomness', 'answer']
    STRUCTURED_FIELDS = {
        'choices': arrayOf('legacy/EGCiphertext'),
        'individual_proofs': arrayOf('legacy/EGZKDisjunctiveProof'),
        'overall_proof' : 'legacy/EGZKDisjunctiveProof',
        'randomness' : 'core/BigInteger'
        }

class EncryptedVote(LegacyObject):
    """
    An encrypted ballot
    """
    FIELDS = ['answers', 'election_hash', 'election_uuid']
    STRUCTURED_FIELDS = {
        'answers' : arrayOf('legacy/EncryptedAnswer')
        }

class Voter(LegacyObject):
    FIELDS = ['election_uuid', 'uuid', 'voter_type', 'voter_id_hash', 'name']

    ALIASED_VOTER_FIELDS = ['election_uuid', 'uuid', 'alias']

    def toDict(self):
        """
        depending on whether the voter is aliased, use different fields
        """
        if self.wrapped_obj.alias != None:
            return super(Voter, self).toDict(self.ALIASED_VOTER_FIELDS)
        else:
            return super(Voter,self).toDict()


class ShortCastVote(LegacyObject):
    FIELDS = ['cast_at', 'voter_uuid', 'voter_hash', 'vote_hash']
    STRUCTURED_FIELDS = {'cast_at' : 'core/Timestamp'}

class CastVote(LegacyObject):
    FIELDS = ['vote', 'cast_at', 'voter_uuid', 'voter_hash', 'vote_hash']
    STRUCTURED_FIELDS = {
        'cast_at' : 'core/Timestamp',
        'vote' : 'legacy/EncryptedVote'}

class Trustee(LegacyObject):
    FIELDS = ['uuid', 'public_key', 'public_key_hash', 'pok', 'decryption_factors', 'decryption_proofs', 'email']

    STRUCTURED_FIELDS = {
        'public_key' : 'legacy/EGPublicKey',
        'pok': 'legacy/DLogProof',
        'decryption_factors': arrayOf(arrayOf('core/BigInteger')),
        'decryption_proofs' : arrayOf(arrayOf('legacy/DLogProof'))}

class EGPublicKey(LegacyObject):
    FIELDS = ['y', 'p', 'g', 'q']
    STRUCTURED_FIELDS = {
        'y': 'core/BigInteger',
        'p': 'core/BigInteger',
        'q': 'core/BigInteger',
        'g': 'core/BigInteger'}

class EGCiphertext(LegacyObject):
    FIELDS = ['alpha','beta']
    STRUCTURED_FIELDS = {
        'alpha': 'core/BigInteger',
        'beta' : 'core/BigInteger'}

class EGZKProofCommitment(LegacyObject):
    FIELDS = ['A', 'B']
    STRUCTURED_FIELDS = {
        'A' : 'core/BigInteger',
        'B' : 'core/BigInteger'}

    def __init__(self, wrapped_obj):
        super(EGZKProofCommitment, self).__init__(DictObject(wrapped_obj))
    
class EGZKProof(LegacyObject):
    FIELDS = ['commitment', 'challenge', 'response']
    STRUCTURED_FIELDS = {
        'commitment': 'legacy/EGZKProofCommitment',
        'challenge' : 'core/BigInteger',
        'response' : 'core/BigInteger'}
        
class EGZKDisjunctiveProof(LegacyObject):
    FIELDS = ['proofs']
    STRUCTURED_FIELDS = {
        'proofs': arrayOf('legacy/EGZKProof')}

    def toDict(self):
        "hijack toDict and make it return the proofs array only, since that's the spec for legacy"
        return super(EGZKDisjunctiveProof, self).toDict()['proofs']

class DLogProof(LegacyObject):
    FIELDS = ['commitment', 'challenge', 'response']
    STRUCTURED_FIELDS = {
        'commitment' : 'core/BigInteger',
        'challenge' : 'core/BigInteger',
        'response' : 'core/BigInteger'}

    def __init__(self, wrapped_obj):
        if type(wrapped_obj) == dict:
            super(DLogProof, self).__init__(DictObject(wrapped_obj))
        else:
            super(DLogProof, self).__init__(wrapped_obj)
