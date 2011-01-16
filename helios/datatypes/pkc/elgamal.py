"""
data types for 2011/01 Helios
"""

from helios.datatypes import LDObject
from helios.crypto import elgamal as crypto_elgamal

class DiscreteLogProof(LDObject):
    FIELDS = ['challenge', 'commitment', 'response']
    STRUCTURED_FIELDS = {
        'challenge' : 'core/BigInteger',
        'commitment' : 'core/BigInteger',
        'response' : 'core/BigInteger'}
    
class PublicKey(LDObject):
    WRAPPED_OBJ_CLASS = crypto_elgamal.PublicKey

    FIELDS = ['y', 'p', 'g', 'q']
    STRUCTURED_FIELDS = {
        'y' : 'core/BigInteger',
        'p' : 'core/BigInteger',
        'g' : 'core/BigInteger',
        'q' : 'core/BigInteger'}


class SecretKey(LDObject):
    WRAPPED_OBJ_CLASS = crypto_elgamal.SecretKey

    FIELDS = ['public_key', 'x']
    STRUCTURED_FIELDS = {
        'public_key' : 'pkc/elgamal/PublicKey',
        'x' : 'core/BigInteger'
        }

class DLogProof(LDObject):
    WRAPPED_OBJ_CLASS = crypto_elgamal.DLogProof
    FIELDS = ['commitment', 'challenge', 'response']

    STRUCTURED_FIELDS = {
        'commitment' : 'core/BigInteger',
        'challenge' : 'core/BigInteger',
        'response' : 'core/BigInteger'}
