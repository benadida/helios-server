"""
data types for 2011/01 Helios
"""

from helios.datatypes import LDObject
from helios.crypto import elgamal

class DiscreteLogProof(LDObject):
    FIELDS = ['challenge', 'commitment', 'response']
    STRUCTURED_FIELDS = {
        'challenge' : 'core/BigInteger',
        'commitment' : 'core/BigInteger',
        'response' : 'core/BigInteger'}
    
class PublicKey(LDObject):
    WRAPPED_OBJ_CLASS = elgamal.PublicKey

    FIELDS = ['y', 'p', 'g', 'q']
    STRUCTURED_FIELDS = {
        'y' : 'core/BigInteger',
        'p' : 'core/BigInteger',
        'g' : 'core/BigInteger',
        'q' : 'core/BigInteger'}

