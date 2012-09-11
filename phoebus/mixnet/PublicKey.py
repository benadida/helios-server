# -*- coding: utf-8 -*-
#
# ============================================================================
# About this file:
# ============================================================================
#
#  PublicKey.py : The public key class.
#
#  Used for data encryption.
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



# ============================================================================
# Imports and constant definitions:
# ============================================================================

import math

# secure version of python's random:
from Crypto.Random.random import StrongRandom
from hashlib import sha256

from EGCryptoSystem import EGCryptoSystem, EGStub
from PVCExceptions import InvalidPloneVoteCryptoFileError
from Ciphertext import Ciphertext
from BitStream import BitStream
import serialize as serialize
# ============================================================================

PublicKey_serialize_structure_definition = {
    "PloneVotePublicKey" : (1, 1, {     # Root element
        "PublicKey" : (1, 1, None),     # exactly 1 PublicKey element
        "CryptoSystemScheme" : (1, 1, { # 1 cryptosystem element, containing:
            "nbits" : (1, 1, None),     # exactly 1 nbits element
            "prime" : (1, 1, None),     # exactly 1 prime element
            "generator" : (1, 1, None)  # exactly 1 generator element
         }),
        "ThresholdKeyInfo" : (0, 1, {  # 0 or 1 occurrences
            "NumTrustees" : (1, 1, None),
            "Threshold" : (1, 1, None),
            "PartialPublicKey" : (1, {  # 1 or more PartialPublicKey elements
                "key" : (1, 1, None),    # exactly 1 key element
                "trustee" : (1, 1, None) # exactly one trustee element
             })
         })
    })
}

# ============================================================================
# Classes:
# ============================================================================


class PublicKey:
    """
    An ElGamal public key object used for encryption.
    
    Attributes:
        cryptosystem::EGCryptoSystem    -- The ElGamal cryptosystem in which 
                                           this key is defined.
    """
    
    def get_fingerprint(self):
        """
        Gets a fingerprint of the current public key.
        
        This fingerprint should be stored with any text encrypted with this 
        public key, in order to facilitate checking compatibility with a 
        particular key pair for future decryption or manipulation.
        
        Returns:
            fingerprint::string -- A SHA256 hexdigest providing a fingerprint 
                                   of the current public key.
        """
        fingerprint = sha256()
        fingerprint.update(hex(self.cryptosystem.get_nbits()))
        fingerprint.update(hex(self.cryptosystem.get_prime()))
        fingerprint.update(hex(self.cryptosystem.get_generator()))
        fingerprint.update(hex(self._key))
        return fingerprint.hexdigest()
    
    def __eq__(self, other):
        """
        Implements PublicKey equality.
        """
        if(isinstance(other, PublicKey) and 
           (other.cryptosystem == self.cryptosystem) and 
           (other._key == self._key)):
            return True
        else:
            return False
    
    def __ne__(self, other):
        """
        Implements PublicKey inequality.
        """
        return not self.__eq__(other)
    
    def __init__(self, cryptosystem, public_key_value):
        """
        Creates a new public key. Should not be invoked directly.
        
        Instead of using this constructor from outside of PloneVoteCryptoLib, 
        please use the class methods EGCryptoSystem.new_key_pair() or 
        PublicKey.from_file(file).
        
        Arguments:
            cryptosystem::EGCryptoSystem-- The ElGamal cryptosystem in which 
                                           this key is defined.
            public_key_value::long        -- The actual value of the public key
                                           (g^a mod p, where a is the priv. key)
        """
        self.cryptosystem = cryptosystem
        self._key = public_key_value
        
    def encrypt_bitstream(self, bitstream, pad_to=None, task_monitor=None):
        """
        Encrypts the given bitstream into a ciphertext object.
        
        Arguments:
            bitstream::BitStream-- A stream of bits to encrypt 
                                   (see BitStream utility class).
            pad_to::int            -- Minimum size (in bytes) of the resulting 
                                   ciphertext. Data will be padded before 
                                   encryption to match this size.
            task_monitor::TaskMonitor    -- A task monitor for this task.
        
        Returns:
            ciphertext:Ciphertext    -- A ciphertext object encapsulating the 
                                       encrypted data.        
        """
        random = StrongRandom()
        
        ## PART 1
        # First, format the bitstream as per Ciphertext.py Note 001,
        # previous to encryption.
        #     [size (64 bits) | message (size bits) | padding (X bits) ]
        ##
        formated_bitstream = BitStream()
        
        # The first 64 encode the size of the actual data in bits
        SIZE_BLOCK_LENGTH = 64
        size_in_bits = bitstream.get_length()
        
        if(size_in_bits >= 2**SIZE_BLOCK_LENGTH):
            raise ValueError("The size of the bitstream to encrypt is larger " \
                             "than 16 Exabits. The current format for  " \
                             "PloneVote ciphertext only allows encrypting a  " \
                             "maximum of 16 Exabits of information.")
        
        formated_bitstream.put_num(size_in_bits, SIZE_BLOCK_LENGTH)
        
        # We then copy the contents of the original bitstream
        bitstream.seek(0)
        formated_bitstream.put_bitstream_copy(bitstream)
        
        # Finally, we append random data until we reach the desired pad_to 
        # length
        unpadded_length = formated_bitstream.get_length()
        if(pad_to != None and (pad_to * 8) > unpadded_length):
            full_length = pad_to * 8
        else:
            full_length = unpadded_length
        
        padding_left = full_length - unpadded_length
        
        while(padding_left > 1024):
            padding_bits = random.randint(1, 2**1024)
            formated_bitstream.put_num(padding_bits,1024)
            padding_left -= 1024
        
        if(padding_left > 0):
            padding_bits = random.randint(1, 2**padding_left)
            formated_bitstream.put_num(padding_bits, padding_left)
            padding_left = 0
        
        ## PART 2
        # We encrypt the formated bitsteam using ElGamal into a Ciphertext 
        # object.
        # See "Handbook of Applied Cryptography" Algorithm 8.18
        ##
        
        # block_size is the size of each block of bits to encrypt
        # since we can only encrypt messages in [0, p - 1]
        # we should use (nbits - 1) as the block size, where 
        # 2**(nbits - 1) < p < 2**nbits
        
        block_size = self.cryptosystem.get_nbits() - 1
        prime = self.cryptosystem.get_prime()
        generator = self.cryptosystem.get_generator()
        
        # We pull data from the bitstream one block at a time and encrypt it
        formated_bitstream.seek(0)
        ciphertext = \
            Ciphertext(self.cryptosystem.get_nbits(), self.get_fingerprint()) 
        
        plaintext_bits_left = formated_bitstream.get_length()
        
        # Check if we have a task monitor and register with it
        if(task_monitor != None):
            # We will do two tick()s per block to encrypt: one for generating 
            # the gamma component of the ciphertext block and another for the 
            # delta component (those are the two time intensive steps, 
            # because of exponentiation). 
            ticks = math.ceil((1.0 * plaintext_bits_left) / block_size) * 2
            encrypt_task_mon = \
                task_monitor.new_subtask("Encrypt data", expected_ticks = ticks)
        
        while(plaintext_bits_left > 0):
        
            # get next block (message, m, etc) to encrypt
            if(plaintext_bits_left >= block_size):
                block = formated_bitstream.get_num(block_size)
                plaintext_bits_left -= block_size
            else:
                block = formated_bitstream.get_num(plaintext_bits_left)
                # Encrypt as if the stream was filled with random data past its 
                # end, this avoids introducing a 0's gap during decryption to 
                # bitstream
                displacement = block_size - plaintext_bits_left
                block = block << displacement
                padding = random.randint(0, 2**displacement - 1)
                assert (padding / 2**displacement == 0), \
                            "padding should be at most displacement bits long"
                block = block | padding
                plaintext_bits_left = 0
            
            # Select a random integer k, 1 <= k <= p − 2
            k = random.randint(1, prime - 2)
            
            # Compute gamma and delta
            gamma = pow(generator, k, prime)
            if(task_monitor != None): encrypt_task_mon.tick()
            
            delta = (block * pow(self._key, k, prime)) % prime
            if(task_monitor != None): encrypt_task_mon.tick()
            
            # Add this encrypted data portion to the ciphertext object
            ciphertext.append(gamma, delta)
        
        # return the ciphertext object
        return ciphertext
        
    
    def encrypt_text(self, text, pad_to=None, task_monitor=None):
        """
        Encrypts the given string into a ciphertext object.
        
        Arguments:
            text::string            -- A string to encrypt.
            pad_to::int            -- Minimum size (in bytes) of the resulting 
                                   ciphertext. Data will be padded before 
                                   encryption to match this size.
            task_monitor::TaskMonitor    -- A task monitor for this task.
        
        Returns:
            ciphertext:Ciphertext    -- A ciphertext object encapsulating the 
                                       encrypted data.
        """
        bitstream = BitStream()
        bitstream.put_string(text)
        return self.encrypt_bitstream(bitstream, pad_to, task_monitor)
        
    def to_file(self, filename, SerializerClass=serialize.XMLSerializer):
        """
        Saves this public key to a file.
        
        Arguments:
            filename::string    -- The path to the file in which to store the 
                                   serialized PublicKey object.
            SerializerClass::class --
                The class that provides the serialization. XMLSerializer by 
                default. Must inherit from serialize.BaseSerializer and provide 
                an adequate serialize_to_file method.
                Note that often the same class used to serialize the data must 
                be used to deserialize it.
                (see utilities/serialize.py documentation for more information)
        """
        # Create a new serializer object for the PublicKey structure definition
        serializer = SerializerClass(PublicKey_serialize_structure_definition)
        
        # Helper function to translate large numbers to their hexadecimal 
        # string representation
        def num_to_hex_str(num):
            hex_str = hex(num)[2:]              # Remove leading '0x'
            if(hex_str[-1] == 'L'): 
                hex_str = hex_str[0:-1]         # Remove trailing 'L'
            return hex_str
        
        # Generate a serializable data dictionary matching the definition:
        prime_str = num_to_hex_str(self.cryptosystem.get_prime())
        generator_str = num_to_hex_str(self.cryptosystem.get_generator())
        data = {
            "PloneVotePublicKey" : {
                "PublicKey" : num_to_hex_str(self._key),
                "CryptoSystemScheme" : {
                    "nbits" : str(self.cryptosystem.get_nbits()),
                    "prime" : prime_str,
                    "generator" : generator_str
                }
            }
        }
        
        # Use the serializer to store the data to file
        serializer.serialize_to_file(filename, data)
        
    @classmethod
    def from_file(cls, filename, SerializerClass=serialize.XMLSerializer):
        """
        Loads an instance of PublicKey from the given file.
        
        Arguments:
            filename::string    -- The name of a file containing the public 
                                   key in serialized form.
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
                                               public key file.
        """
        # Create a new serializer object for the PublicKey structure definition
        serializer = SerializerClass(PublicKey_serialize_structure_definition)
        
        # Deserialize the PublicKey instance from file
        try:
            data = serializer.deserialize_from_file(filename)
        except serialize.InvalidSerializeDataError, e:
            # Convert the exception to an InvalidPloneVoteCryptoFileError
            raise InvalidPloneVoteCryptoFileError(filename, 
                "File \"%s\" does not contain a valid public key. The " \
                "following error occurred while trying to deserialize the " \
                "file contents: %s" % (filename, str(e)))
                
        # Verify that we are dealing with a single public key and not a 
        # threshold public key. In the later case, call 
        # ThresholdPublicKey.from_file on the given file, instead of this 
        # method.
        if(data["PloneVotePublicKey"].has_key("ThresholdKeyInfo")):
	    raise NotImplementedError
            from plonevotecryptolib.Threshold.ThresholdPublicKey import \
                                              ThresholdPublicKey
            return ThresholdPublicKey.from_file(filename, SerializerClass)
                
        # Helper function to decode numbers from strings and 
        # raise an exception if the string is not a valid number.
        # (value_name is used only to construct the exception string).
        def str_to_num(num_str, base, value_name):
            try:
                return int(num_str, base)
            except ValueError:
                raise InvalidPloneVoteCryptoFileError(filename, 
                    "File \"%s\" does not contain a valid public key. The " \
                    "stored value for %s is not a valid integer in " \
                    "base %d representation." % (filename, value_name, base))
                    
        # Get the values from the deserialized data
        inner_elems = data["PloneVotePublicKey"]["CryptoSystemScheme"]
        nbits = str_to_num(inner_elems["nbits"], 10, "nbits")
        prime = str_to_num(inner_elems["prime"], 16, "prime")
        generator = str_to_num(inner_elems["generator"], 16, "generator")
        
        pub_key = str_to_num(data["PloneVotePublicKey"]["PublicKey"], 
                                  16, "PublicKey")
        
        # Check the loaded values
        if(not (1 <= pub_key <= prime - 2)):
            raise InvalidPloneVoteCryptoFileError(filename, 
                "File \"%s\" does not contain a valid public key. The value " \
                "of the public key given in the file does not match the " \
                "indicated cryptosystem. Could the file be corrupt?" % filename)
        
        # Construct the cryptosystem object
        cryptosystem = EGCryptoSystem.load(nbits, prime, generator)
        
        # Construct and return the PublicKey object
        return cls(cryptosystem, pub_key)
