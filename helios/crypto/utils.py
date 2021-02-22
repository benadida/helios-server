"""
Crypto Utils
"""
import base64
import math

from Crypto.Hash import SHA256
from Crypto.Random.random import StrongRandom

random = StrongRandom()


def random_mpz_lt(maximum, strong_random=random):
    n_bits = int(math.floor(math.log(maximum, 2)))
    res = strong_random.getrandbits(n_bits)
    while res >= maximum:
        res = strong_random.getrandbits(n_bits)
    return res


random.mpz_lt = random_mpz_lt


def hash_b64(s):
    """
    hash the string using sha256 and produce a base64 output
    removes the trailing "="
    """
    hasher = SHA256.new(s.encode('utf-8'))
    result = base64.b64encode(hasher.digest())[:-1].decode('ascii')
    return result
