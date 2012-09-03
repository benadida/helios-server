# -*- coding: utf-8 -*-
#
# ============================================================================
# About this file:
# ============================================================================
#
#  KeyPair.py : A class representing a private/public key pair.
#
#  Used to create an represent a newly created private/public key pair.
#
#  Part of the PloneVote cryptographic library (PloneVoteCryptoLib)
#
#  Originally written by: Lazaro Clapp
#
# ============================================================================
# LICENSE (MIT License - http://www.opensource.org/licenses/mit-license):
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# ============================================================================

# secure version of python's random:
from Crypto.Random.random import StrongRandom

from EGCryptoSystem import EGCryptoSystem
from PublicKey import PublicKey
from PrivateKey import PrivateKey

class KeyPair:
    """
    A key pair object.
    
    Both this object's constructor and the new(EGCryptoSystem) method can be 
    used to generate a new pair of private and corresponding public key.
    
    Attributes:
        public_key::PublicKey    -- The public key
        private_key::PrivateKey  -- The private key    
    """
    # ^ Redundant attribute description is redundant... redundantly
    
    def __init__(self, cryptosystem):
        """
        Generates a new key pair for the given EGCryptoSystem
        """
        p = cryptosystem.get_prime()
        random = StrongRandom()
        
        inner_private_key = random.randint(1, p - 2)
        
        self.private_key = PrivateKey(cryptosystem, inner_private_key)
        self.public_key = self.private_key.public_key

