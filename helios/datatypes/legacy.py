"""
Legacy datatypes for Helios (v3.0)
"""

from helios.datatypes import LDObject, arrayOf

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
    FIELDS = ['choices', 'individual_proofs', 'overall_proof', 'randomness', 'answer']
    STRUCTURED_FIELDS = {
        'choices': arrayOf('pkc/elgamal/Ciphertext'),
        'individual_proofs': arrayOf('pkc/elgamal/DisjunctiveProof'),
        'overall_proof' : 'pkc/elgamal/DisjunctiveProof',
        'randomness' : 'core/BigInteger'
        # answer is not a structured field, it's an as-is integer
        }

class Voter(LegacyObject):
    FIELDS = ['election_uuid', 'uuid', 'voter_type', 'voter_id_hash', 'name', 'alias']

    ALIASED_VOTER_FIELDS = ['election_uuid', 'uuid', 'alias']

    def toDict(self):
        """
        depending on whether the voter is aliased, use different fields
        """
        if self.wrapped_obj.alias != None:
            return super(Voter, self).toDict(self.ALIASED_VOTER_FIELDS)
        else:
            return super(Voter,self).toDict()


class CastVote(LegacyObject):
    FIELDS = ['vote', 'cast_at', 'voter_uuid', 'voter_hash', 'vote_hash']

class Trustee(LegacyObject):
    FIELDS = ['uuid', 'public_key', 'public_key_hash', 'pok', 'decryption_factors', 'decryption_proofs', 'email']

    STRUCTURED_FIELDS = {
        'public_key' : 'legacy/EGPublicKey',
        'pok': 'legacy/DLogProof',
        'decryption_factors': arrayOf('core/BigInteger'),
        'decryption_proofs' : arrayOf('legacy/DLogProof')}

class EGPublicKey(LegacyObject):
    FIELDS = ['y', 'p', 'g', 'q']
    STRUCTURED_FIELDS = {
        'y': 'core/BigInteger',
        'p': 'core/BigInteger',
        'q': 'core/BigInteger',
        'g': 'core/BigInteger'}
