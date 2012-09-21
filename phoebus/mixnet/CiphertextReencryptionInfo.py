# -*- coding: utf-8 -*-
#
# ============================================================================
# About this file:
# ============================================================================
#
#  CiphertextReencryptionInfo.py :
#
#  This file provides CiphertextReencryptionInfo, a class for storing the
#  information used to re-encrypt a particular Ciphertext into another, namely
#  the re-encryption coefficients (g^{r'}, y^{r'}) for each block of
#  ciphertext. Given the two ciphertexts and this information, the fact
#  that they both are different encryptions of the same plaintext can be
#  verified without decryption.
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

from Ciphertext import Ciphertext

from PVCExceptions import (IncompatibleCiphertextError,
                           IncompatibleReencryptionInfoError)


class CiphertextReencryptionInfo:
    """
    Stores the information used to re-encrypt a ciphertext into another.

    Using this class outside of PloneVoteCryptoLib is not recommended. Within
    plonevotecryptolib.Mixnet, only CiphertextCollection, Mixer and
    ShufflingProof should be used by most clients.

    This class stores a list of re-encryption coefficients (g^{r'}, y^{r'}),
    one for each block of ciphertext. Objects of this class are both indexable
    and iterable, and behave as a list of pairs (g^{r'}, y^{r'}) when accessed
    so.

    Given the two ciphertexts and the corresponding CiphertextReencryptionInfo
    object, the fact that they both are different encryptions of the same
    plaintext can be verified without decryption. If the origin ciphertext is
    A, the re-encrypted ciphertext is B, and the reencryption info object is R,
    then B[i] = R[i]*A[i] = (g^{r'}*gamma, y^{r'}*delta) for all i. This
    comparison can be performed through the verify() method of this class.

    The new() class/static method can be used to generate a new random
    re-encryption that can then be applied to a ciphertext through the
    apply() method, resulting in the re-encrypted ciphertext.

    (See [TODO: Add reference] for more infomation).

    Attributes:
        public_key::PublicKey   -- The public key used for re-encryption.
                                   This must be the same public key used to
                                   encrypt the original ciphertext.
    """

    # NOTE: Would just storing r' per block instead of (g^{r'}, y^{r'})
    # be secure?
    # The answer seems to be yes, consider refactoring

    @classmethod
    def from_dict(cls, d, pk, nbits):
        reenc = cls(pk)
        for block in d['blocks']:
            reenc._blocks.append(block)

        return reenc

    def to_dict(self):
        data = {'blocks': []}
        for block in self._blocks:
            data['blocks'].append(block)
        return data

    def get_length(self):
        """
        Returns the length in blocks of the re-encryption information.
        """
        return len(self._blocks)

    def __getitem__(self, i):
        """
        Makes this object indexable.

        Returns:
            (g^{r'}, y^{r'})::(long, long)  -- Returns the ith block of
                                               re-encryption information.
        """
        length = len(self._blocks)
        if(not (0 <= i < length)):
            return ValueError("Index out of range: Got %d, expected index " \
                              "between 0 and %d." % (i, length-1))

        return self._blocks[i]

    def __iter__(self):
        """
        Return an iterator for the current CiphertextReencryptionInfo.
        """
        return self._blocks.__iter__()

    def __init__(self, public_key):
        """
        Constructs a new (empty) CiphertextReencryptionInfo object.

        Arguments:
            (See class attributes)
        """
        self.public_key = public_key
        self._blocks = []

    def add_block(self, gr, yr):
        """
        Adds a new block of re-encryption information to this object.

        Arguments:
            gr::long   -- The g^{r'} component of the re-encryption information.
            yr::long   -- The y^{r'} component of the re-encryption information.
                          (Where y is the public key value)
        """
        self._blocks.append((gr, yr))

    @classmethod
    def new(cls, public_key, length):
        """
        Generate a new re-encryption information object with the given length.

        This constructs {length} blocks of random ciphertext re-encryption
        information, which can be applied to a given ciphertext in order to
        produce a re-encrypted ciphertext.

        Arguments:
            public_key::PublicKey-- The public key to be used for re-encryption.
                                   This must be the same public key that was
                                   used to encrypt the original ciphertext.
            length::int -- Number of blocks of re-encryption information.

        Returns:
            reencryption_info::CiphertextReencryptionInfo   --
                A new CiphertextReencryptionInfo object containing length
                random blocks or re-encryption information.
        """
        random = StrongRandom()

        # Get p and g
        prime = public_key.cryptosystem.get_prime()
        generator = public_key.cryptosystem.get_generator()

        # Create a new empty CiphertextReencryptionInfo object
        reencryption_info = CiphertextReencryptionInfo(public_key)

        # Add (length) random re-encryption information blocks
        for i in range(0, length):

            # Select a random integer r, 1 <= r <= p − 2
            r = random.randint(1, prime - 2)

            # store block (g^{r}, y^{r})
            gr = pow(generator, r, prime)
            yr = pow(public_key._key, r, prime)
            reencryption_info.add_block(gr, yr)

        assert (reencryption_info.get_length() == length)

        return reencryption_info

    def apply(self, ciphertext):
        """
        Re-encrypts the given ciphertext with this re-encryption information.

        Arguments:
            ciphertext::Ciphertext -- The ciphertext to be re-encrypted.

        Returns:
            reencrypted_ciphertext::Ciphertext  -- A re-encryption of
                ciphertext performed with this re-encryption information.

        Throws:
            IncompatibleCiphertextError --
                If the ciphertext and this re-encryption information are not
                compatible. Either because their length in blocks differs, or
                because they don't have the same public key.
        """
        # Check length compatibility
        if(ciphertext.get_length() != self.get_length()):
            raise IncompatibleCiphertextError("The given ciphertext is " \
                "incompatible with this re-encryption information object: " \
                "The two objects have different length. There are %d blocks "\
                "of ciphertext and %d blocks of re-encryption information." \
                % (ciphertext.get_length(), self.get_length()))

        # Check key compatibility
        if(ciphertext.pk_fingerprint != self.public_key.get_fingerprint()):
            raise IncompatibleCiphertextError("The given ciphertext is " \
                "incompatible with this re-encryption information object: " \
                "The public key used to encrypt the ciphertext is different " \
                "from the one used to generate this re-encryption " \
                "information object.")

        # Get nbits and p
        nbits = self.public_key.cryptosystem.get_nbits()
        prime = self.public_key.cryptosystem.get_prime()

        # For each block of the ciphertext, apply the corresponding block of
        # re-encryption.
        reencrypted_ciphertext = Ciphertext(nbits, ciphertext.pk_fingerprint)
        for i in range(0, self.get_length()):
            gamma, delta = ciphertext[i]
            gr, yr = self[i]
            new_gamma = (gr * gamma) % prime
            new_delta = (yr * delta) % prime
            reencrypted_ciphertext.append(new_gamma, new_delta)

        return reencrypted_ciphertext

    def verify(self, original_ciphertext, reencrypted_ciphertext):
        """
        Verify the re-encryption between two ciphertexts.

        Given ciphertexts A and B, check whether B is a re-encryption of A
        performed using this re-encryption information. That is, if applying
        this re-encryption information to A produces B as a result.

        Arguments:
            original_ciphertext::Ciphertext -- (A) The original ciphertext that
                                               was purportedly re-encrypted.
            reencrypted_ciphertext::Ciphertext -- (B) The ciphertext we wish to
                                                  verify is a re-encryption of
                                                  the original ciphertext A
                                                  performed with the current
                                                  re-encryption information.

        Returns:
            result::bool    -- True if reencrypted_ciphertext is a
                               re-encryption of original_ciphertext performed
                               with this re-encryption information.
                               False otherwise.
        """
        try:
            original_reencrypted = self.apply(original_ciphertext)
        except IncompatibleCiphertextError:
            return False

        return (original_reencrypted == reencrypted_ciphertext)

    def subtract(self, other_reencryption):
        """
        Subtracts another re-encryption from the current re-encryption.

        Subtraction of re-encryptions works block by block: if the ith block of
        the current re-encryption is (g^{r_1}, y^{r_1}), and the ith block of
        the other re-encryption given is (g^{r_2}, y^{r_2}), then the ith block
        of the subtraction is (g^{r_1 - r_2}, y^{r_1 - r_2}).

        Note that if we are given c1, a re-encryption of ciphertext c with
        re-encryption information R1, and c2 a re-encryption of c with
        re-encryption information R2, then R = R2.subtract(R1) is the
        re-encryption information for a valid (verifiable) re-encryption from
        c1 to c2.

        Re-encryption subtraction only works on re-encryptions created with
        the same public key.

        We define this as a new method instead of using operator overloading
        for (-), because the semantics of re-encryption information subtraction
        are not obvious.

        Arguments:
            other_reencryption::CiphertextReencryptionInfo  --
                A re-encryption information to object to subtract from this one.

        Returns:
            result::CiphertextReencryptionInfo --
                The subtraction of other_reencryption to this re-encryption
                information object, as defined in the explanation above.

        Throws:
            IncompatibleReencryptionInfoError   --
                If the re-encryptions are not compatible for subtraction.
                Either because they are of different length or they were
                created with a different public key.
        """
        # Check length compatibility
        if(other_reencryption.get_length() != self.get_length()):
            raise IncompatibleReencryptionInfoError("The re-encryption " \
                "information objects are incompatible: The two objects have " \
                "different length. There are %d blocks of re-encryption " \
                "information on the current object and %d blocks of " \
                "re-encryption information in the object passed as a " \
                "parameter." \
                % (self.get_length(), other_reencryption.get_length()))

        # Check key compatibility
        pk_fingerprint_self = self.public_key.get_fingerprint()
        pk_fingerprint_other = other_reencryption.public_key.get_fingerprint()

        if(pk_fingerprint_other != pk_fingerprint_self):
            raise IncompatibleCiphertextError("The re-encryption " \
                "information objects are incompatible: The two objects have " \
                "were created with different public keys.")

        # Get nbits and p
        nbits = self.public_key.cryptosystem.get_nbits()
        prime = self.public_key.cryptosystem.get_prime()

        # Create a new empty re-encryption to hold the subtraction
        result = CiphertextReencryptionInfo(self.public_key)

        # Perform the subtraction of self - other_reencryption block by block
        # and store it on result.
        for i in range(0, self.get_length()):
             gr1, yr1 = self[i]                     # g^{r_1} and y^{r_1}
             gr2, yr2 = other_reencryption[i]       # g^{r_2} and y^{r_2}

             # Remember that we can invert in Z_p by elevating to p - 2.
             inv_gr2 = pow(gr2, prime - 2, prime)   # (g^{r_2})^{-1} = g^{-r_2}
             inv_yr2 = pow(yr2, prime - 2, prime)   # (y^{r_2})^{-1} = y^{-r_2}

             gr = (gr1*inv_gr2) % prime             # g^{r_1 - r_2}
             yr = (yr1*inv_yr2) % prime             # y^{r_1 - r_2}

             result.add_block(gr, yr)

        return result

