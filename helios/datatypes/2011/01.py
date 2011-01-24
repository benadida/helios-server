"""
data types for 2011/01 Helios
"""

from helios.datatypes import LDObject, arrayOf, DictObject, ListObject

class Trustee(LDObject):
  """
  a trustee
  """
  
  FIELDS = ['uuid', 'public_key', 'public_key_hash', 'pok', 'decryption_factors', 'decryption_proofs', 'email']
  STRUCTURED_FIELDS = {
    'pok' : 'pkc/elgamal/DiscreteLogProof',
    'public_key' : 'pkc/elgamal/PublicKey'
    }

  # removed some public key processing for now
 
class Election(LDObject):
  FIELDS = ['uuid', 'questions', 'name', 'short_name', 'description', 'voters_hash', 'openreg',
            'frozen_at', 'public_key', 'cast_url', 'use_advanced_audit_features', 
            'use_voter_aliases', 'voting_starts_at', 'voting_ends_at']
  
  STRUCTURED_FIELDS = {
    'public_key' : 'pkc/elgamal/PublicKey',
    'voting_starts_at': 'core/Timestamp',
    'voting_ends_at': 'core/Timestamp',
    'frozen_at': 'core/Timestamp',
    'questions': '2011/01/Questions',
    }

class Voter(LDObject):
    FIELDS = ['election_uuid', 'uuid', 'voter_type', 'voter_id_hash', 'name']

class EncryptedAnswer(LDObject):
    FIELDS = ['choices', 'individual_proofs', 'overall_proof', 'randomness', 'answer']
    STRUCTURED_FIELDS = {
        'choices': arrayOf('pkc/elgamal/EGCiphertext'),
        'individual_proofs': arrayOf('pkc/elgamal/DisjunctiveProof'),
        'overall_proof' : 'pkc/elgamal/DisjunctiveProof',
        'randomness' : 'core/BigInteger'
        # answer is not a structured field, it's an as-is integer
        }


class Questions(ListObject, LDObject):
    WRAPPED_OBJ = list

