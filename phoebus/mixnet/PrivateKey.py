# -*- coding: utf-8 -*-
#
# ============================================================================
# About this file:
# ============================================================================
#
#  PublicKey.py : The private key class.
#
#  Used for data decryption.
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

from EGCryptoSystem import EGCryptoSystem, EGStub
from PublicKey import PublicKey
from Ciphertext import Ciphertext
from PVCExceptions import InvalidPloneVoteCryptoFileError, \
                          IncompatibleCiphertextError
from BitStream import BitStream
import serialize as serialize
# ============================================================================

PrivateKey_serialize_structure_definition = {
    "PloneVotePrivateKey" : (1, 1, {    # Root element
        "PrivateKey" : (1, 1, None),    # exactly 1 PrivateKey element
        "CryptoSystemScheme" : (1, 1, { # 1 cryptosystem element, containing:
            "nbits" : (1, 1, None),     # exactly 1 nbits element
            "prime" : (1, 1, None),     # exactly 1 prime element
            "generator" : (1, 1, None)  # exactly 1 generator element
         })
    })
}

# ============================================================================
# Classes:
# ============================================================================

class PrivateKey:
    """
    An ElGamal private key object used for decryption.
    
    Attributes:
        cryptosystem::EGCryptoSystem    -- The ElGamal cryptosystem in which 
                                           this key is defined.
        public_key::PublicKey    -- The associated public key.
    """
    
    def __eq__(self, other):
        """
        Implements PrivateKey equality.
        """
        if(isinstance(other, PrivateKey) and 
           (other.cryptosystem == self.cryptosystem) and 
           (other.public_key == self.public_key) and  
           (other._key == self._key)):
            return True
        else:
            return False
    
    def __ne__(self, other):
        """
        Implements PrivateKey inequality.
        """
        return not self.__eq__(other)
    
    def __init__(self, cryptosystem, private_key_value):
        """
        Creates a new private key. Should not be invoked directly.
        
        Instead of using this constructor from outside of PloneVoteCryptoLib, 
        please use the class methods EGCryptoSystem.new_key_pair() or 
        PrivateKey.from_file(file).
        
        Arguments:
            cryptosystem::EGCryptoSystem-- The ElGamal cryptosystem in which 
                                           this key is defined.
            private_key_value::long     -- The actual value of the private key.
        """        
        public_key_value = pow(cryptosystem.get_generator(), 
                               private_key_value, 
                               cryptosystem.get_prime())
        
        self.cryptosystem = cryptosystem
        self.public_key = PublicKey(cryptosystem, public_key_value)
        self._key = private_key_value
        
    def decrypt_to_bitstream(self, ciphertext, task_monitor=None, force=False):
        """
        Decrypts the given ciphertext into a bitstream.
        
        If the bitstream was originally encrypted with PublicKey.encrypt_X(), 
        then this method returns a bitstream following the format described 
        in Note 001 of the Ciphertext.py file:
            [size (64 bits) | message (size bits) | padding (X bits) ]
        
        Arguments:
            ciphertext::Ciphertext    -- An encrypted Ciphertext object.
            task_monitor::TaskMonitor    -- A task monitor for this task.
            force:bool    -- Set this to true if you wish to force a decryption 
                           attempt, even when the ciphertext's stored public key
                           fingerprint does not match that of the public key 
                           associated with this private key.
        
        Returns:
            bitstream::Bitstream    -- A bitstream containing the unencrypted 
                                       data.
        
        Throws:
            IncompatibleCiphertextError -- The given ciphertext does not appear 
                                           to be decryptable with the selected 
                                           private key.
        """
        # Check that the public key fingerprint stored in the ciphertext 
        # matches the public key associated with this private key.
        if(not force):
            if(ciphertext.nbits != self.cryptosystem.get_nbits()):
                raise IncompatibleCiphertextError("The given ciphertext is " \
                        "not decryptable with the selected private key: " \
                        "incompatible cryptosystem/key sizes.")
            
            if(ciphertext.pk_fingerprint != self.public_key.get_fingerprint()):
                raise IncompatibleCiphertextError("The given ciphertext is " \
                        "not decryptable with the selected private key: " \
                        "public key fingerprint mismatch.")
        
        # We read and decrypt the ciphertext block by block
        # See "Handbook of Applied Cryptography" Algorithm 8.18
        bitstream = BitStream()
        
        block_size = self.cryptosystem.get_nbits() - 1
        prime = self.cryptosystem.get_prime()
        key = self._key
        
        # Check if we have a task monitor and register with it
        if(task_monitor != None):
            # One tick per block
            ticks = ciphertext.get_length()
            decrypt_task_mon = \
                task_monitor.new_subtask("Decrypt data", expected_ticks = ticks)
        
        for gamma, delta in ciphertext:
            assert max(gamma, delta) < 2**(block_size + 1), \
                "The ciphertext object includes blocks larger than the " \
                "expected block size."
            m = (pow(gamma, prime - 1 - key, prime) * delta) % prime
            bitstream.put_num(m, block_size)
            
            if(task_monitor != None): decrypt_task_mon.tick()
            
        return bitstream
            
    
    def decrypt_to_text(self, ciphertext, task_monitor=None, force=False):
        """
        Decrypts the given ciphertext into its text contents as a string
        
        This method assumes that the ciphertext contains an encrypted stream of 
        data in the format of Note 001 of the Ciphertext.py file, were message 
        contains string information (as opposed to a binary format).
            [size (64 bits) | message (size bits) | padding (X bits) ]
        
        Arguments:
            ciphertext::Ciphertext    -- An encrypted Ciphertext object, 
                                       containing data in the above format.
            task_monitor::TaskMonitor    -- A task monitor for this task.
            force:bool    -- Set to true if you wish to force a decryption 
                           attempt, even when the ciphertext's stored public 
                           key fingerprint does not match that of the public 
                           key associated with this private key.
        
        Returns:
            string::string    -- Decrypted message as a string.
        
        Throws:
            IncompatibleCiphertextError -- The given ciphertext does not appear 
                                           to be decryptable with the selected 
                                           private key.
        """
        bitstream = self.decrypt_to_bitstream(ciphertext, task_monitor, force)
        bitstream.seek(0)
        length = bitstream.get_num(64)
        return bitstream.get_string(length)
    
    def to_file(self, filename, SerializerClass=serialize.XMLSerializer):
        """
        Saves this private key to a file.
        
        Arguments:
            filename::string    -- The path to the file in which to store the 
                                   serialized PrivateKey object.
            SerializerClass::class --
                The class that provides the serialization. XMLSerializer by 
                default. Must inherit from serialize.BaseSerializer and provide 
                an adequate serialize_to_file method.
                Note that often the same class used to serialize the data must 
                be used to deserialize it.
                (see utilities/serialize.py documentation for more information)
        """
        # Create a new serializer object for the PrivateKey structure definition
        serializer = SerializerClass(PrivateKey_serialize_structure_definition)
        
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
            "PloneVotePrivateKey" : {
                "PrivateKey" : num_to_hex_str(self._key),
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
        Loads an instance of PrivateKey from the given file.
        
        Arguments:
            filename::string    -- The name of a file containing the private 
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
                                               private key file.
        """
        # Create a new serializer object for the PrivateKey structure definition
        serializer = SerializerClass(PrivateKey_serialize_structure_definition)
        
        # Deserialize the PrivateKey instance from file
        try:
            data = serializer.deserialize_from_file(filename)
        except serialize.InvalidSerializeDataError, e:
            # Convert the exception to an InvalidPloneVoteCryptoFileError
            raise InvalidPloneVoteCryptoFileError(filename, 
                "File \"%s\" does not contain a valid private key. The " \
                "following error occurred while trying to deserialize the " \
                "file contents: %s" % (filename, str(e)))
                
        # Helper function to decode numbers from strings and 
        # raise an exception if the string is not a valid number.
        # (value_name is used only to construct the exception string).
        def str_to_num(num_str, base, value_name):
            try:
                return int(num_str, base)
            except ValueError:
                raise InvalidPloneVoteCryptoFileError(filename, 
                    "File \"%s\" does not contain a valid private key. The " \
                    "stored value for %s is not a valid integer in " \
                    "base %d representation." % (filename, value_name, base))
                    
        # Get the values from the deserialized data
        inner_elems = data["PloneVotePrivateKey"]["CryptoSystemScheme"]
        nbits = str_to_num(inner_elems["nbits"], 10, "nbits")
        prime = str_to_num(inner_elems["prime"], 16, "prime")
        generator = str_to_num(inner_elems["generator"], 16, "generator")
        
        priv_key = str_to_num(data["PloneVotePrivateKey"]["PrivateKey"], 
                                  16, "PrivateKey")
        
        # Check the loaded values
        if(not (1 <= priv_key <= prime - 2)):
            raise InvalidPloneVoteCryptoFileError(filename, 
                "File \"%s\" does not contain a valid private key. The value " \
                "of the private key given in the file does not match the " \
                "indicated cryptosystem. Could the file be corrupt?" % filename)
        
        # Construct the cryptosystem object
        cryptosystem = EGCryptoSystem.load(nbits, prime, generator)
        
        # Construct and return the PrivateKey object
        return cls(cryptosystem, priv_key)
