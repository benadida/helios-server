# -*- coding: utf-8 -*-
#
# ============================================================================
# About this file:
# ============================================================================
#
#  CiphertextCollection.py : A class to represent a collection of ciphertexts.
#
#  This class is essentially a container for a list of Ciphertext objects
#  encrypted with the same public key.
#  Additionally, it implements the shuffle_with_proof() method, which provides
#  a verifiable shuffling of the ciphertext collection into a different
#  collection encapsulating the same plaintexts.
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

from PVCExceptions import (InvalidCiphertextCollectionMappingError,
                           IncompatibleCiphertextCollectionError,
                           IncompatibleCiphertextError)

class CiphertextCollection:
    """
    An object representing an ordered collection of ciphertexts.

    This object allows storing an ordered collection of Ciphertext objects and
    provides indexing and iteration over said collection. All ciphertexts in
    the collection must have been encrypted with the same public key, so that
    they can be treated uniformly for shuffling.

    The shuffle_with_proof() method can be used to verifiably shuffle the
    ciphertext collection into a different collection encapsulating the same
    plaintexts.

    This class can be stored to and loaded to an XML file.

    Attributes:
        public_key::PublicKey   -- The public key that was used to encrypt all
                                   ciphertexts in the collection.
    """

    @classmethod
    def from_dict(cls, d, pk, nbits):
        from .Ciphertext import Ciphertext
        coll = cls(pk)
        for cipher_data in d['ciphertexts']:
            cipher = Ciphertext(nbits, pk.get_fingerprint())
            cipher.gamma = cipher_data['a']
            cipher.delta = cipher_data['b']
            coll._ciphertexts.append(cipher)

        return coll

    def to_dict(self):
        data = {'ciphertexts': []}
        for cipher in self._ciphertexts:
            data['ciphertexts'].append(cipher.to_dict())

        return data

    def get_length(self):
        """
        Returns the number of ciphertexts in the collection.
        """
        return len(self._ciphertexts)


    def __getitem__(self, i):
        """
        Makes this object indexable.

        Returns:
            ciphertext::Ciphertext  -- Returns the ith ciphertext in the
                                       collection. Index start at 0.
        """
        length = len(self._ciphertexts)
        if(not (0 <= i < length)):
            return ValueError("Index out of range: Got %d, expected index " \
                              "between 0 and %d." % (i, length-1))

        return self._ciphertexts[i]


    def __iter__(self):
        """
        Return an iterator for the current ciphertext collection.
        """
        return self._ciphertexts.__iter__()


    def __eq__(self, other):
        """
        Implements CiphertextCollection equality.

        Two ciphertext collections are equal if they have the same number of
        elements and those elements are equal and in the same order. A
        CiphertextCollection object is not equal to any object of a different
        type.
        """
        if(not isinstance(other, CiphertextCollection)):
            return False

        if(other.get_length() != self.get_length()):
            return False

        for i in range(0, self.get_length()):
            if(other[i] != self[i]):
                return False

        return True


    def __ne__(self, other):
        """
        Implements CiphertextCollection inequality.

        See __eq__(...) for the definition of CiphertextCollection equality,
        inequality its is negation.
        """
        return not self.__eq__(other)


    def __init__(self, public_key):
        """
        Constructs a new (empty) CiphertextCollection.

        Arguments:
            (See class attributes)
        """
        self.public_key = public_key
        # Cache the fingerprint to improve performance
        self._pk_fingerprint = self.public_key.get_fingerprint()
        self._ciphertexts = []


    def add_ciphertext(self, ciphertext):
        """
        Adds a new Ciphertext object to the CiphertextCollection.

        Arguments:
            ciphertext::Ciphertext  -- The ciphertext to add.

        Throws:
            IncompatibleCiphertextError -- If the given ciphertext was not
                                           encrypted with the public key for
                                           this collection.
        """
        # Check that the ciphertext was encrypted with the correct public key
        # for this collection.
        if(ciphertext.pk_fingerprint != self._pk_fingerprint):
            raise IncompatibleCiphertextError("The given ciphertext is " \
                "incompatible with this collection and cannot be added: It " \
                "was not encrypted with the public key declared for the " \
                "collection.")

        # Add the ciphertext
        self._ciphertexts.append(ciphertext)


    def shuffle_with_proof(self):
        """
        Produce a verifiable shuffle of this ciphertext collection.

        This method returns a tuple containing a new CiphertextCollection
        object, which encodes the same plaintexts as the current collection
        but reencrypted and randomly permuted, and a zero-knowledge proof of
        shuffling.

        The proof of shuffling can be used (via the ShuffleProof.verify(...)
        method) to check that both collections contain encryptions of the same
        set of plaintexts, under the same cryptosystem and public key. On the
        other hand, neither the collections nor the proof give any information
        regarding which ciphertext in the first collection corresponds to which
        ciphertext in the second, shuffled, collection (hence why we say the
        proof is done in zero-knowledge).

        (see Josh Benaloh, "Simple Verifiable Elections",
        http://www.usenix.org/event/evt06/tech/full_papers/benaloh/benaloh.pdf
        for more information.)

        Returns:
            (shuffled_collection, proof)::
                (CiphertextCollection, ShufflingProof)
                --

                    shuffled_collection is a shuffled version of the current
                collection, containing different ciphertexts but encoding the
                same plaintexts as the current collection (in different order).

                    proof is a zero-knowledge proof asserting that the current
                collection and shuffled_collection are the equivalent
                (that is, contain representations of the same plaintext in
                equal numbers). This proof can be verified through the
                verify(...) method of ShuffleProof itself.

        Throws:
            ValueError --
                If params.SHUFFLING_PROOF_SECURITY_PARAMETER is within an
                invalid range.
        """
        # Import CiphertextCollectionMapping and ShufflingProof

        ## Note:
        #   python has some well known issues with circular imports
        #   (see http://effbot.org/zone/import-confusion.htm) so putting this
        #   import statements at the top of our module in the usual way
        #   will not work.
        #
        #   Besides, CiphertextCollection as a class is conceptually at a lower
        #   layer of our architecture than both these other classes. Only this
        #   convenience method, designed to make the API easier to use from
        #   outside of plonevotecryptolib, depends on those classes. So it
        #   actually makes more sense to import these classes within this
        #   method only.
        ##
        from CiphertextCollectionMapping import CiphertextCollectionMapping
        from ShufflingProof import ShufflingProof

        # Create a mapping from the current collection into a random shuffling
        mapping = CiphertextCollectionMapping.new(self)

        # Apply the mapping to obtain the resulting shuffled collection
        try:
            shuffled_collection = mapping.apply(self)
        except IncompatibleCiphertextCollectionError:
            assert False, "IncompatibleCiphertextCollectionError may not be " \
                        "raised when applying a mapping M created using " \
                        "CiphertextCollectionMapping.new(C) to the same C."

        # Generate the zero-knowledge proof of shuffling
        try:
            proof = ShufflingProof.new(self, shuffled_collection, mapping)
        except InvalidCiphertextCollectionMappingError:
            assert False, "InvalidCiphertextCollectionMappingError may not be " \
                        "raised when shuffled_collection was created from the " \
                        "original collection (self) by applying the mapping."

        # Form tuple and return it
        return (shuffled_collection, proof)

