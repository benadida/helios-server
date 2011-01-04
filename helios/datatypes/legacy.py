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
        'public_key' : 'legacy/EGPublicKey'
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
    pass

class CastVote(LegacyObject):
    pass

class Trustee(LegacyObject):
    pass
