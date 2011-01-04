"""
data types for 2011/01 Helios
"""

from helios.datatypes import LDObject

class DiscreteLogProof(LDObject):
    FIELDS = ['challenge', 'commitment', 'response']
    STRUCTURED_FIELDS = {
        'challenge' : 'core/BigInteger',
        'commitment' : 'core/BigInteger',
        'response' : 'core/BigInteger'}
    
class PublicKey(LDObject):
    FIELDS = ['y', 'p', 'g', 'q']
    STRUCTURED_FIELDS = {
        'y' : 'core/BigInteger',
        'p' : 'core/BigInteger',
        'g' : 'core/BigInteger',
        'q' : 'core/BigInteger'}

