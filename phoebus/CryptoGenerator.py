#
#   ElGamal.py : ElGamal encryption/decryption and signatures
#
#  Part of the Python Cryptography Toolkit
#
#  Originally written by: A.M. Kuchling
#
# ===================================================================
# The contents of this file are dedicated to the public domain.  To
# the extent that dedication to the public domain is not available,
# everyone is granted a worldwide, perpetual, royalty-free,
# non-exclusive license to exercise all rights associated with the
# contents of this file for any purpose whatsoever.
# No rights are reserved.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ===================================================================

__revision__ = "$Id$"

from Crypto.PublicKey.pubkey import *
from Crypto.Util import number

class error (Exception):
    pass

# Generate an ElGamal key with N bits
def generate(bits, randfunc, progress_func=None):
    """generate(bits:int, randfunc:callable, progress_func:callable)

    Generate an ElGamal key of length 'bits', using 'randfunc' to get
    random data and 'progress_func', if present, to display
    the progress of the key generation.
    """
    obj=ElGamalobj()
    # Generate a safe prime p
    # See Algorithm 4.86 in Handbook of Applied Cryptography
    counter = 0
    while 1:
        if progress_func:
            progress_func('p [%d]\r' % counter)
        counter += 1
        #q = bignum(number.getStrongPrime(bits-1, e=0, false_positive_prob=1e-6, randfunc=randfunc))
        q = bignum(number.getPrime(bits-1, randfunc=randfunc))
        obj.p = 2*q+1
        if number.isPrime(obj.p, randfunc=randfunc):
            break
    if progress_func:
        progress_func('p              \n')
    counter = 0
    # Generate generator g
    # See Algorithm 4.80 in Handbook of Applied Cryptography
    # Note that the order of the group is n=p-1=2q, where q is prime
    while 1:
        # We must avoid g=2 because of Bleichenbacher's attack described
        # in "Generating ElGamal signatures without knowning the secret key",
        # 1996
        #
        if progress_func:
            progress_func('g [%d]\r' % counter)
        counter += 1

        obj.g = number.getRandomRange(2**196, obj.p, randfunc)
        safe = 1
        if pow(obj.g, 2, obj.p)==1:
            safe=0
        if safe and pow(obj.g, q, obj.p)==1:
            safe=0
        # Discard g if it divides p-1 because of the attack described
        # in Note 11.67 (iii) in HAC
        if safe and divmod(obj.p-1, obj.g)[1]==0:
            safe=0
        # g^{-1} must not divide p-1 because of Khadir's attack
        # described in "Conditions of the generator for forging ElGamal
        # signature", 2011
        ginv = number.inverse(obj.g, obj.p)
        if safe and divmod(obj.p-1, ginv)[1]==0:
            safe=0
        if safe:
            break
    # Generate private key x
    if progress_func:
        progress_func('g             \n')
        progress_func('x\n')

    obj.x=number.getRandomRange(2**196, obj.p-1, randfunc)
    # Generate public key y
    if progress_func:
        progress_func('y\n')
    obj.y = pow(obj.g, obj.x, obj.p)
    return obj

def construct(tuple):
    """construct(tuple:(long,long,long,long)|(long,long,long,long,long)))
             : ElGamalobj
    Construct an ElGamal key from a 3- or 4-tuple of numbers.
    """

    obj=ElGamalobj()
    if len(tuple) not in [3,4]:
        raise ValueError('argument for construct() wrong length')
    for i in range(len(tuple)):
        field = obj.keydata[i]
        setattr(obj, field, tuple[i])
    return obj

class ElGamalobj(pubkey):
    keydata=['p', 'g', 'y', 'x']

    def _encrypt(self, M, K):
        a=pow(self.g, K, self.p)
        b=( M*pow(self.y, K, self.p) ) % self.p
        return ( a,b )

    def _decrypt(self, M):
        if (not hasattr(self, 'x')):
            raise TypeError('Private key not available in this object')
        ax=pow(M[0], self.x, self.p)
        plaintext=(M[1] * inverse(ax, self.p ) ) % self.p
        return plaintext

    def _sign(self, M, K):
        if (not hasattr(self, 'x')):
            raise TypeError('Private key not available in this object')
        p1=self.p-1
        if (GCD(K, p1)!=1):
            raise ValueError('Bad K value: GCD(K,p-1)!=1')
        a=pow(self.g, K, self.p)
        t=(M-self.x*a) % p1
        while t<0: t=t+p1
        b=(t*inverse(K, p1)) % p1
        return (a, b)

    def _verify(self, M, sig):
        if sig[0]<1 or sig[0]>self.p-1:
            return 0
        v1=pow(self.y, sig[0], self.p)
        v1=(v1*pow(sig[0], sig[1], self.p)) % self.p
        v2=pow(self.g, M, self.p)
        if v1==v2:
            return 1
        return 0

    def size(self):
        "Return the maximum number of bits that can be handled by this key."
        return number.size(self.p) - 1

    def has_private(self):
        """Return a Boolean denoting whether the object contains
        private components."""
        if hasattr(self, 'x'):
            return 1
        else:
            return 0

    def publickey(self):
        """Return a new key object containing only the public information."""
        return construct((self.p, self.g, self.y))


#object=ElGamalobj

def main_generate():
    from Crypto.Random import new
    from sys import stderr
    randfunc = new().read
    def process_func(msg):
        stderr.write("%s" % (msg,))
        stderr.flush()

    C = generate(2048, randfunc, process_func)
    print C
    print C.p, C.g, C.y, C.x

if __name__ == '__main__':
    main_generate()
    pass

