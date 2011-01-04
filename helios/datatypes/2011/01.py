"""
data types for 2011/01 Helios
"""

from helios.datatypes import LDObject

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
    pass
