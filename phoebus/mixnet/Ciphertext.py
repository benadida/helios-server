# -*- coding: utf-8 -*-
#
# ============================================================================
# About this file:
# ============================================================================
#
#  Ciphertext.py : A class to represent encrypted data within PloneVoteCryptoLib.
#
#  This class is mostly used to represent encrypted data in memory and to
#  store/load that data to/from file.
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

## Note 001:
#
# By convention (followed across PloneVoteCryptoLib), before being encrypted,
# all data is transformed into an array of bytes formated as follows:
#
# - The first 64 bits (8 bytes) are a long representation of the size of
# the encrypted data ($size).
# - The next $size bits are the original data to be encrypted.
# - The rest of the array contains random padding.
#
#    [size (64 bits) | message (size bits) | padding (X bits) ]
#
# Note that this limits messages to be encrypted to 16 Exabits (2 Exabytes).
# We deem this enough for our purposes (in fact, votes larger than a couple MB
# are highly unlikely, and system memory is probably going to be a more
# immediate problem).
#
##

# ============================================================================
# Imports and constant definitions:
# ============================================================================

from hashlib import sha256

from PVCExceptions import InvalidPloneVoteCryptoFileError
from BitStream import BitStream
import serialize as serialize
# ============================================================================

Ciphertext_serialize_structure_definition = {
    "PloneVoteCiphertext" : (1, 1, {    # Root element
        "nbits" : (1, 1, None),         # exactly 1 nbits element
        "PKFingerprint" : (1, 1, None), # exactly 1 PKFingerprint element
        "EncryptedData" : (1, 1, None)  # exactly 1 EncryptedData element
    })
}

# ============================================================================
# Classes:
# ============================================================================

class CiphertextIterator:
    """
    An iterator object for a Ciphertext.

    It works block by block returning the (gamma, delta) pair for each block.
    """

    def __init__(self,ciphertext):
        """
        Constructs a new iterator.

        Arguments:
            ciphertext::Ciphertext    -- the ciphertext object through which we
                                       wish to iterate.
        """
        self.ciphertext = ciphertext
        self._pos = 0
        self._max = ciphertext.get_length()

    def next(self):
        """
        Retrieve next block in the ciphertext.

        Returns:
            (gamma, delta)::(long, long)    -- The gamma and delta pair
                                               representing a block of ElGamal
                                               encrypted ciphertext.
        """
        if(self._pos == self._max):
            raise StopIteration
        pair = self.ciphertext[self._pos]
        self._pos += 1
        return pair


class Ciphertext:
    """
    An object representing encrypted PloneVote data.

    Ciphertext objects are created by PublicKey encrypt operations and
    decrypted through PrivateKey decrypt methods (or through
    ThresholdDecryptionCombinator if the data was encrypted with a threshold
    public key and all partial decryptions are available).

    This class can also be store to and loaded from file using the PloneVote
    armored ciphertext XML format.

    Attributes:
        nbits::int    -- Size in bits of the cryptosystem/public key used to
                       encrypt this ciphertext.
        pk_fingerprint::string -- A fingerprint of the public key used to
                                  encrypt this ciphertext. This fingerprint can
                                  then be compared with the result from
                                  PublicKey.get_fingerprint() to check for
                                  compatibility with a given key pair or
                                  threshold public key.
        gamma::long[]
        delta::long[]    -- :
            This two attributes should only be accessed by key classes within
            PloneVoteCryptoLib.
            See "Handbook of Applied Cryptography" Algorithm 8.18 for the
            meaning of the variables. An array is used because the encrypted
            data might be longer than the cryptosystem's bit size.
    """

    def to_dict(self):
        return {'a': self.gamma, 'b': self.delta}

    def get_length(self):
        """
        Returns the length, in blocks, of the ciphertext.
        """
        assert len(self.gamma) == len(self.delta), "Each gamma component of " \
                                            "the ciphertext must correspond " \
                                            " to one delta component."
        return len(self.gamma)

    def __getitem__(self, i):
        """
        Makes this object indexable.

        Returns:
            (gamma, delta)::(long, long)    -- Returns the gamma, delta pair
                                               representing a particular block
                                               of the encrypted data.
                Use ciphertext[i] for block i.
        """
        return (self.gamma[i], self.delta[i])

    def __iter__(self):
        """
        Return an iterator (CiphertextIterator) for the current ciphertext.
        """
        return CiphertextIterator(self)

    def __eq__(self, other):
        """
        Implements Ciphertext equality.

        Two ciphertexts are equal if they have the same bit size, public key
        fingerprint and list of gamma and delta components. A ciphertext is not
        equal to any object of a different type.
        """
        if(isinstance(other, Ciphertext) and
           (other.nbits == self.nbits) and
           (other.pk_fingerprint == self.pk_fingerprint) and
           (other.gamma == self.gamma) and
           (other.delta == self.delta)):
            return True
        else:
            return False

    def __ne__(self, other):
        """
        Implements Ciphertext inequality.

        See __eq__(...) for the definition of Ciphertext equality,
        inequality its is negation.
        """
        return not self.__eq__(other)

    def get_fingerprint(self):
        """
        Gets a fingerprint of the current ciphertext.

        A ciphertext fingerprint is generated as a SHA-256 hash of the
        ciphertext, block by block.

        Returns:
            fingerprint::string -- A SHA-256 hexdigest providing a fingerprint
                                   of the current ciphertext.
        """
        fingerprint = sha256()
        for (gamma, delta) in self:
            fingerprint.update(hex(gamma))
            fingerprint.update(hex(delta))
        return fingerprint.hexdigest()

    def __init__(self, nbits, public_key_fingerprint):
        """
        Create an empty ciphertext object.

        Arguments:
            nbits::int    -- Size in bits of the cryptosystem/public key used
                             to encrypt this ciphertext.
            public_key_fingerprint::string    -- The fingerprint of the public
                                               key used to encrypt this data.
        """
        self.gamma = []
        self.delta = []
        self.nbits = nbits
        self.pk_fingerprint = public_key_fingerprint

    def append(self, gamma, delta):
        """
        Used internally by PublicKey.

        This method adds an encrypted block of data with its gamma and delta
        components from ElGamal (see HoAC Alg. 8.18).
        """
        self.gamma.append(gamma)
        self.delta.append(delta)

    def _encrypted_data_as_bitstream(self):
        """
        Returns the contents of this ciphertext as a BitStream object.

        This includes only the encrypted data (gamma and delta components), not
        the nbits and public key fingerprint metadata.

        The components are encoded alternating as follows:
            [gamma[0], delta[0], gamma[1], delta[1], ...]
        with each component represented as a nbits long number.

        Returns:
            bitstream::BitStream    -- The gamma and delta components of this
                                       ciphertext as a bitstream.
        """
        bitstream = BitStream()
        for i in range(0, self.get_length()):
            bitstream.put_num(self.gamma[i], self.nbits)
            bitstream.put_num(self.delta[i], self.nbits)
        return bitstream

    def _encrypted_data_as_base64(self):
        """
        Returns the contents of this ciphertext as a base64 string.

        This includes only the encrypted data (gamma and delta components), not
        the nbits and public key fingerprint metadata.
        """
        bitstream = self._encrypted_data_as_bitstream()
        bitstream.seek(0)
        length = bitstream.get_length()

        assert length % 8 == 0, \
                "The ciphertext data must be a multiple of eight bits in size."

        return bitstream.get_base64(length)

    def to_file(self, filename, SerializerClass=serialize.XMLSerializer):
        """
        Saves this ciphertext to a file.

        Arguments:
            filename::string    -- The path to the file in which to store the
                                   serialized Ciphertext object.
            SerializerClass::class --
                The class that provides the serialization. XMLSerializer by
                default. Must inherit from serialize.BaseSerializer and provide
                an adequate serialize_to_file method.
                Note that often the same class used to serialize the data must
                be used to deserialize it.
                (see utilities/serialize.py documentation for more information)
        """
        # Create a new serializer object for the Ciphertext structure definition
        serializer = SerializerClass(Ciphertext_serialize_structure_definition)

        # Generate a serializable data dictionary matching the definition:
        data = {
            "PloneVoteCiphertext" : {
                "nbits" : str(self.nbits),
                "PKFingerprint" : self.pk_fingerprint,
                "EncryptedData" : self._encrypted_data_as_base64()
            }
        }

        # Use the serializer to store the data to file
        serializer.serialize_to_file(filename, data)

    @classmethod
    def from_file(cls, filename, SerializerClass=serialize.XMLSerializer):
        """
        Loads an instance of Ciphertext from the given file.

        Arguments:
            filename::string    -- The name of a file containing the ciphertext
                                   in serialized form.
            SerializerClass::class --
                The class that provides the deserialization. XMLSerializer by
                default. Must inherit from serialize.BaseSerializer and provide
                an adequate deserialize_from_file method.
                Note that often the same class used to serialize the data must
                be used to deserialize it.
                (see utilities/serialize.py documentation for more information)

        Throws:
            InvalidPloneVoteCryptoFileError -- If the file is not a valid
                                               PloneVoteCryptoLib stored
                                               ciphertext file.
        """
        # Create a new serializer object for the Ciphertext structure definition
        serializer = SerializerClass(Ciphertext_serialize_structure_definition)

        # Deserialize the Ciphertext instance from file
        try:
            data = serializer.deserialize_from_file(filename)
        except serialize.InvalidSerializeDataError, e:
            # Convert the exception to an InvalidPloneVoteCryptoFileError
            raise InvalidPloneVoteCryptoFileError(filename,
                "File \"%s\" does not contain a valid ciphertext. The " \
                "following error occurred while trying to deserialize the " \
                "file contents: %s" % (filename, str(e)))

        # Get the values from the deserialized data
        try:
            nbits = int(data["PloneVoteCiphertext"]["nbits"])
        except ValueError:
            raise InvalidPloneVoteCryptoFileError(filename,
                    "File \"%s\" does not contain a valid ciphertext. The " \
                    "stored value for nbits is not a valid (decimal) integer." \
                    % filename)

        fingerprint_str = data["PloneVoteCiphertext"]["PKFingerprint"]
        enc_data_str = data["PloneVoteCiphertext"]["EncryptedData"]

        # Construct a new Ciphertext object with the given nbits and fingerprint
        ciphertext = cls(nbits, fingerprint_str)

        # Load the encrypted data
        bitstream = BitStream()
        bitstream.put_base64(enc_data_str)
        bitstream.seek(0)
        length = bitstream.get_length()

        #     number of gamma and delta blocks in the bitstream:
        blocks = length / (nbits * 2)

        for i in range(0, blocks):
            gamma_val = bitstream.get_num(nbits)
            delta_val = bitstream.get_num(nbits)
            ciphertext.append(gamma_val, delta_val)

        # Return the ciphertext
        return ciphertext
