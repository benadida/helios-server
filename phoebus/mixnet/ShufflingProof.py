# -*- coding: utf-8 -*-
#
# ============================================================================
# About this file:
# ============================================================================
#
#  ShufflingProof.py :
#
#  This file provides ShufflingProof, a class storing a verifiable
#  Zero-Knowledge proof of correct shuffling between two ciphertext
#  collections. Given two CiphertextCollection objects and their corresponding
#  ShufflingProof, it can be verified that both collections contain
#  re-encryptions of the same collection of plaintexts (including repetitions
#  of the same plaintext). Additionally, this verification is done in
#  Zero-Knowledge in the sense that the information contained within
#  ShufflingProof objects does not reveal (fully or partially) the mapping of
#  particular ciphertexts from the origin collection to the shuffled one.
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

from hashlib import sha256

# Use configuration parameters from params.py
import params
import multiprocessing

from BitStream import BitStream

from CiphertextCollection import CiphertextCollection
from CiphertextCollectionMapping import CiphertextCollectionMapping, \
    new_collection_mapping

# Exceptions:
from PVCExceptions import InvalidCiphertextCollectionMappingError


class ShufflingProof:
    """
    Stores the Zero-Knowledge proof of shuffling between two CiphertextCollection objects.

    This class contains a probabilistic Zero-Knowledge proof of equivalence
    between a ciphertext collection and a collection obtained from it by a
    shuffling operation.

    The recomended way to produce a shuffled CiphertextCollection from an
    existing CiphertextCollection, together with their Zero-Knowledge proof of
    equivalence (as a ShufflingProof object), is to use the
    shuffle_with_proof() method of CiphertextCollection.

    To verify (in Zero-Knowledge) that two collections are shown to be
    equivalent by this proof, we use the verify(...) method of the proof,
    passing it both the original and the shuffled collection. Of course, two
    collections might be equivalent without the current ShufflingProof object
    showing so, in which case verify(...) will return False for those
    collections. ShufflingProof.verify(...), for any possible ShufflingProof
    object, will not return True for two collections that are not really
    equivalent, save with negligible probability.

    From within plonevotecryptolib.Mixnet, we can also use the new(...) class
    method of this class to create a new proof of equivalence between
    ciphertext collections A and B, providing both collections and a valid
    CiphertextCollectionMapping between them.
    """

    ## SOME NOTES ON THE INTERNALS OF THIS PROOF:
    #
    # A shuffling/mixing proof is a probabilistic Zero-Knowledge proof in which
    # the challenge is created non-interactively by means of the Fiat-Shamir
    # heuristic. Practical explanation below, full explanation in:
    #
    #   Josh Benaloh, "Simple Verifiable Elections"
    #   http://www.usenix.org/event/evt06/tech/full_papers/benaloh/benaloh.pdf
    #   [ToDo: Add own reference]
    #
    # This proof requires an integer security parameter P.
    # In plonevotecryptolib, this parameter is taken from
    #  params.SHUFFLING_PROOF_SECURITY_PARAMETER
    #
    # A ShufflingProof has three private fields:
    #
    #   * self._collections: A list of P collections, purportedly generated as
    #   shuffles of the same original collection (the original collection we
    #   wish to prove is equivalent to a particular shuffled collection)
    #
    #   * self._mappings: A list of P mappings (CiphertextCollectionMapping),
    #   each either from the original collection into the ith element of
    #   self._collections, or from that same element into the destination
    #   shuffled collection we wish to prove equivalent (never both).
    #
    #   * self._challenge: A challenge stored as a string representing a
    #   hexadecimal number, where, if b is the value of the ith bit of that
    #   number in binary representation:
    #       (b == 0) => self._mappings[i] is a mapping from the original
    #           collection into self._collections[i].
    #       (b == 1) => self._mappings[i] is a mapping from self._collections[i]
    #           into the destination shuffled collection.
    #   (Storing the challenge is not really necessary, but it can make some
    #   diagnostics easier, allowing us to know what part of the proof failed.)
    #
    #
    # To generate a proof of shuffling (the new(...) method), between original
    # collection O and shuffled destination collection D, with mapping M (O->D):
    #
    #   1) P CiphertextCollection objects, equivalent to O, are generated
    #      (using new CiphertextCollectionMapping objects) and used to populate
    #      self._collections.
    #
    #   2) A fingerprint (SHA-256) of all involved collections, including O, D
    #      and those in self._collections, is generated as a challenge c.
    #
    #   3) We store c as self._challenge = c.
    #
    #   4) Using M, the mappings generated in (1), and the
    #      CiphertextCollectionMapping.rebase(...) operation, self._mappings is
    #      populated in accordance with self._challenge.
    #
    #   5) All information not stored in the fields self._collections,
    #      self._mapping and self._challenge is forgotten by the ShufflingProof
    #      object, so that the proof conveys no knowledge of the mapping M
    #      between O and D, other than that such mapping must exist.
    #
    # To verify the proof (the verify(...) method):
    #
    #   1) The challenge c is generated again.
    #
    #   2) self._challenge is verified to be c.
    #
    #   3) Each self._mapping[i] is verified to be a correct mapping from O to
    #      self._collections[i] or from self._collections[i] to D, as dictated
    #      by self._challenge.
    ##

    def __init__(self):
        """
        Constructs a new empty ShufflingProof.

        This method should not be used outside of this class. Consider using
        ShufflingProof.new(...) or CiphertextCollection.shuffle_with_proof().
        """
        self._collections = []
        self._mappings = []
        self._challenge = None


    @classmethod
    def from_dict(cls, d, pk, nbits):
        from .CiphertextCollectionMapping import CiphertextCollectionMapping
        from .CiphertextCollection import CiphertextCollection

        proof = cls()
        proof._challenge = d['challenge']

        for mapping_data in d['mappings']:
            proof._mappings.append(CiphertextCollectionMapping.from_dict(mapping_data,
                                                                        pk,
                                                                         nbits))

        for collection_data in d['collections']:
            proof._collections.append(CiphertextCollection.from_dict(collection_data,
                                                                    pk, nbits))

        return proof

    def to_dict(self):
        if not self._challenge:
            raise Exception("Uninitialized shuffling")

        data = {'collections': [], 'mappings': [], 'challenge': None}
        for mapping in self._mappings:
            data['mappings'].append(mapping.to_dict())

        for collection in self._collections:
            data['collections'].append(collection.to_dict())

        data['challenge'] = self._challenge
        return data


    def _generate_challenge(self, original_collection, shuffled_collection):
        """
        Generates the challenge used to construct and verify the proof.

        This challenge is constructed as a SHA-256 hash of the
        original_collection, shuffled_collection and the collections in
        self._collections. This general scheme is known as the Fiat-Shamir
        heuristic and allows us to make the zero-knowledge shuffling proof
        non-interactive.

        Arguments:
            original_collection::CiphertextCollection --
                The original collection to be shuffled.
            shuffled_collection::CiphertextCollection --
                The shuffled collection resulting from applying mapping to
                original_collection.

        Returns:
            challenge::string - A 256-bit challenge, as a hexadecimal number
                encoded as a string.
        """

        # NOTE: self._collection must already be populated with its final
        # values for this method to give the expected result.

        # We generate the challenge c as a SHA-256 hash of all collections,
        # including original_collection (O), shuffled_collection (D) and those
        # in self._collections.
        #
        # Each collection is hashed ciphertext by ciphertext, in order, and
        # each ciphertext is hashed block by block, in order.
        #
        # Collections order: O -> self._collections[i] by increasing index -> D
        #
        # Finally, the fingerprint for the public key of the original_collection
        # (which must be the same as for all ciphertexts and collections taken
        # into account) is added to the hash as well.

        c = sha256()

        for ciphertext in original_collection:
            for (gamma, delta) in ciphertext:
                c.update(hex(gamma))
                c.update(hex(delta))

        for collection in self._collections:
            for ciphertext in collection:
                for (gamma, delta) in ciphertext:
                    c.update(hex(gamma))
                    c.update(hex(delta))

        for ciphertext in shuffled_collection:
            for (gamma, delta) in ciphertext:
                c.update(hex(gamma))
                c.update(hex(delta))

        c.update(original_collection.public_key.get_fingerprint())

        hexdigest = c.hexdigest()

        return hexdigest


    @classmethod
    def new(cls, original_collection, shuffled_collection, mapping):
        """
        Constructs a new proof of equivalence between original_collection and
        shuffled_collection.

        This method should not be used outside of plonevotecryptolib.Mixnet.
        Consider using CiphertextCollection.shuffle_with_proof() instead.

        The given CiphertextCollectionMapping must be a valid mapping between
        original_collection and shuffled_collection.

        Arguments:
            original_collection::CiphertextCollection --
                The original collection to be shuffled.
            shuffled_collection::CiphertextCollection --
                The shuffled collection resulting from applying mapping to
                original_collection.
            mapping::CiphertextCollectionMapping --
                The mapping between original_collection and shuffled_collection.

        Returns:
            proof::ShufflingProof --
                The zero-knowledge proof of equivalence between
                original_collection and shuffled_collection.

        Throws:
            InvalidCiphertextCollectionMappingError --
                If mapping is not a valid mapping between original_collection
                and shuffled_collection.
            ValueError --
                If params.SHUFFLING_PROOF_SECURITY_PARAMETER is within an
                invalid range.
        """
        # Check that we have a valid mapping between the two collections:
        if(not mapping.verify(original_collection, shuffled_collection)):
            raise InvalidCiphertextCollectionMappingError( \
                    "mapping was expected to be a CiphertextCollectionMapping "\
                    "object representing a valid mapping between "\
                    "original_collection and shuffled_collection. However, "\
                    "mapping.verify(original_collection, shuffled_collection) "\
                    "returns False. A zero-knowledge proof of equivalence "\
                    "between two shuffled collections cannot be constructed "\
                    "without first having a valid mapping between them.")

        # Get the security parameter P
        security_parameter = params.SHUFFLING_PROOF_SECURITY_PARAMETER

        # Check that the security parameter is <= 256, since that is the most
        # bits of challenge we can currently have. Also check that P is at least 1
        if(security_parameter < 1 or security_parameter > 256):
            raise ValueError("Security parameter for shuffling proof " \
                    "(params.SHUFFLING_PROOF_SECURITY_PARAMETER) is out of " \
                    "range. The security parameter must be between 1 and 256, "\
                    "its current value is %d. If you have set " \
                    "CUSTOM_SHUFFLING_PROOF_SECURITY_PARAMETER in the file " \
                    "params.py, please correct this value or set it to None, " \
                    "in order for the security parameter to be decided based " \
                    "on the global SECURITY_LEVEL of plonevotecryptolib. It " \
                    "is recommended that " \
                    "CUSTOM_SHUFFLING_PROOF_SECURITY_PARAMETER be always set " \
                    "to None for deployment operation of plonevotecryptolib." \
                    % security_parameter)

        # Construct a new empty proof
        proof = ShufflingProof()

        # Populate proof._collections with P random shuffles of
        # original_collection. We save each mapping for now in proof._mappings.
        # (ie. every mapping in proof._mappings[i] will initially be from the
        # original collection into proof._collections[i])

        # generate new mappings in parallel
        pool = multiprocessing.Pool()
        async_params = [original_collection] * security_parameter
        generate_mappings_pool = pool.map_async(new_collection_mapping, async_params)
        for new_mapping in generate_mappings_pool.get(99999999):
            proof._mappings.append(new_mapping)
            proof._collections.append(new_mapping.apply(original_collection))
        pool.close()
        pool.join()

        # Generate the challenge
        proof._challenge = \
            proof._generate_challenge(original_collection, shuffled_collection)

        # Get the challenge as a BitStream for easier manipulation
        challenge_bits = BitStream()
        challenge_bits.put_hex(proof._challenge)
        challenge_bits.seek(0)  # back to the beginning of the stream

        # For each of the first P bits in the stream
        for i in range(0, security_parameter):
            ## print "Processing challenge bit %d" % i # replace with TaskMonitor API calls
            bit = challenge_bits.get_num(1)
            if(bit == 0):
                # Do nothing.
                # proof._mappings[i] is already a mapping from
                # original_collection unto proof._collections[i]
                pass
            elif(bit == 1):
                # Change proof._mappings[i] to be a mapping from
                # proof._collections[i] unto shuffled_collection, using
                # CiphertextCollectionMapping.rebase(...)

                # rebase(O->D, O->C_{i}) => C_{i}->D
                rebased_mapping = mapping.rebase(proof._mappings[i])

                # Replace O->C_{i} with C_{i}->D
                proof._mappings[i] = rebased_mapping
            else:
                assert False, "We took a single bit, its value must be either "\
                        "0 or 1."

        # return the proof object
        return proof


    def verify(self, original_collection, shuffled_collection):
        """
        Verifies that original_collection and shuffled_collection are
        equivalent as proven by this ShufflingProof object.

        If this method returns true, then we have proof that both collections
        contain encryptions of the same collection of plaintexts, save for the
        negligible probability (for a correct security parameter configured in
        params.py) that the zero-knowledge proof has been faked. Otherwise we
        gain no information about the two collections, other than they are not
        shown to be equivalent by this particular proof.

        ShufflingProof is a zero-knowledge proof: the result of this
        verification or the information within the ShufflingProof object for
        which two collections pass this verification, provide no information as
        to the association of particular ciphertexts in original_collection
        with particular ciphertexts of shuffled_collection.

        Arguments:
            original_collection::CiphertextCollection   --
                The original collection of ciphertexts.
            shuffled_collection::CiphertextCollection   --
                Another collection for which we wish to know if the current
                ShufflingProof object demonstrates equivalence with
                original_collection.

        Returns:
            result::bool    -- True if this proof shows both collections to be
                               equivalent.
                               False otherwise.
        """
        # Get the security parameter P with which the proof was originally
        # created. This is reflect in the length of self._collections and
        # self._mappings.
        assert len(self._collections) == len(self._mappings), \
            "The length of the private properties self._collections and " \
            "self._mappings of ShufflingProof must always be the same."
        security_parameter = len(self._collections)


        # Get the security parameter specified in params
        minimum_allowed_security_parameter = params.SHUFFLING_PROOF_SECURITY_PARAMETER

        # Check that the security parameter is <= 256, since that is the most
        # bits of challenge we can currently have. Also check that P is at least 1
        if(minimum_allowed_security_parameter < 1 or
           minimum_allowed_security_parameter > 256):
            raise ValueError("Security parameter for shuffling proof " \
                    "(params.SHUFFLING_PROOF_SECURITY_PARAMETER) is out of " \
                    "range. The security parameter must be between 1 and 256, "\
                    "its current value is %d. If you have set " \
                    "CUSTOM_SHUFFLING_PROOF_SECURITY_PARAMETER in the file " \
                    "params.py, please correct this value or set it to None, " \
                    "in order for the security parameter to be decided based " \
                    "on the global SECURITY_LEVEL of plonevotecryptolib. It " \
                    "is recommended that " \
                    "CUSTOM_SHUFFLING_PROOF_SECURITY_PARAMETER be always set " \
                    "to None for deployment operation of plonevotecryptolib." \
                    % security_parameter)

        # Check that the security parameter for which the proof was generated
        # is correct and meets the security standards declared in params.py
        if(security_parameter < minimum_allowed_security_parameter or
           security_parameter < 1 or
           security_parameter > 256):
            raise InvalidShuffilingProofError("The security parameter for " \
                    "(which the current proof was created is %d. This is " \
                    "(either an incorrect value (outside of the [1,256] " \
                    "(range) or not secure enough to meet the standards set " \
                    "(in the configuration of params.py (< %d). The proof " \
                    "(is thus invalid." \
                    % (security_parameter,
                      minimum_allowed_security_parameter))

        # Generate the challenge
        challenge = \
            self._generate_challenge(original_collection, shuffled_collection)

        # Verify that the challenge corresponds to the stored one
        if(challenge != self._challenge):
            return False

        # Get the challenge as a BitStream for easier manipulation
        challenge_bits = BitStream()
        challenge_bits.put_hex(challenge)
        challenge_bits.seek(0)  # back to the beginning of the stream

        # For each of the first P bits in the stream
        for i in range(0, security_parameter):
            bit = challenge_bits.get_num(1)
            if(bit == 0):
                # verify that self._mapping[i] maps original_collection into
                # self._collections[i]
                if(not self._mappings[i].verify(original_collection,
                                               self._collections[i])):
                    return False

            elif(bit == 1):
                # verify that self._mapping[i] self._collections[i] into
                # self._collections[i]
                if(not self._mappings[i].verify(self._collections[i],
                                               shuffled_collection)):
                    return False
            else:
                assert False, "We took a single bit, its value must be either "\
                        "0 or 1."

        # If we made it so far, the proof is correct
        # (each mapping is in accordance to the challenge and valid)
        return True
