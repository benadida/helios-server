"""
Crypto Utils
"""
import base64

from Crypto.Hash import SHA256
from Crypto.Random.random import StrongRandom

random = StrongRandom()


def random_mpz_lt(maximum, strong_random=random):
    """
    Uniformly sample an integer in [0, maximum).

    n_bits must be the exact bit length of maximum, not floor(log2(maximum)):
    the latter is one too small for every maximum that isn't a power of two,
    which caps the output at 2^(n_bits) - 1 < maximum. The rejection loop below
    then never fires and the top slice of the range is never sampled (5.6% of
    the range for the default 256-bit q), biasing every exponent drawn here.

    Raises ValueError for a non-positive maximum, which names no valid result:
    the rejection loop would otherwise spin forever, since every draw is >= 0.
    """
    if maximum <= 0:
        raise ValueError("maximum must be positive, got %r" % (maximum,))

    n_bits = maximum.bit_length()
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
