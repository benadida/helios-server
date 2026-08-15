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

    Sizing the draw with maximum.bit_length() is what leaves the rejection loop
    below any work to do. This used to size it with floor(log2(maximum)), which
    is one bit short for every maximum that isn't a power of two: getrandbits
    could then only return values below 2^(bit_length - 1), already less than
    maximum. Nothing was ever rejected, and the top slice of [0, maximum) was
    never sampled -- 5.6% of the range for the default 256-bit q -- biasing
    every exponent drawn here.

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
