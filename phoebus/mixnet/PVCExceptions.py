# -*- coding: utf-8 -*-
#
#  PVCExceptions.py : Custom exceptions used by PloneVoteCryptoLib.
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

class ParameterError(Exception):
    """
    Parameter error exception.
    
    The base exception for when invalid parameters are fed to the 
    PloneVoteCryptoLib public classes and methods.

    Attributes:
        msg::string -- explanation of the error
    """
    
    def __str__(self):
        return self.msg

    def __init__(self, msg):
        """Create a new ParameterError exception
        """
        self.msg = msg

class ElectionSecurityError(Exception):
    """
    Election security error exception.
    
    This exception is used as the base for exceptions within PloneVoteCryptoLib 
    which would seem to indicate a security problem, such as an intentional 
    attack, a corrupt proof used for verification (of decryption, of threshold 
    set-up, of shuffling, etc). Applications using PloneVoteCryptoLib should be 
    careful when handling ElectionSecurityErrors and not allow the election 
    process to continue until the error has been resolved.

    Attributes:
        msg::string -- explanation of the error
    """
    
    def __str__(self):
        return self.msg

    def __init__(self, msg):
        """Create a new ElectionSecurityError exception
        """
        self.msg = msg

class KeyLengthTooLowError(ParameterError):
    """
    Key length (or cryptosystem bit size) too low exception.
    
    Exception raised when the length of the keys or the size in bits given 
    for the cryptosystem fall below the minimum allowed and thus may not be 
    secure enough. 
    
    (This minimum can be configured in params)

    Attributes:
        given_size::int     -- the (invalid) key or cryptosystem bit size  
                               requested by the user
        minimum_size::int   -- the minimum key or cryptosystem bit size allowed
        msg::string         -- explanation of the error
    """

    def __init__(self, given_size, minimum_size, msg):
        """Create a new KeyLengthTooLowError exception
        """
        self.given_size = given_size
        self.minimum_size = minimum_size
        ParameterError.__init__(self, msg)


class KeyLengthNonBytableError(ParameterError):
    """
    Key length (or cryptosystem bit size) is not expressible in bytes.
    
    Exception raised when the length of the keys or the size in bits given 
    for the cryptosystem is not a multiple of 8 and thus the resulting 
    cryptosystem cannot easily encrypt and decrypt byte arrays. Currently,
    key sizes that are not expressible in whole bytes are not permitted by 
    PloneVoteCryptoLib. 

    Attributes:
        given_size::int     -- the (invalid) key or cryptosystem bit size  
                               requested by the user
        msg::string         -- explanation of the error
    """

    def __init__(self, given_size, msg):
        """Create a new KeyLengthNonBytableError exception
        """
        self.given_size = given_size
        ParameterError.__init__(self, msg)


class KeyLengthMismatch(ParameterError):
    """
    Given key length and the length of a parameter, such as the crypsystem's 
    prime, do not match.

    Attributes:
        msg::string         -- explanation of the error
    """

    def __init__(self, msg):
        """Create a new KeyLengthMismatch exception
        """
        ParameterError.__init__(self, msg)


class NotASafePrimeError(ParameterError):
    """
    Given number is not a safe prime.
    
    Exception raised when a number claimed to be a safe prime for an ElGamal 
    scheme is not really a safe prime. 

    Attributes:
        num::int    -- the given number
        msg::string -- explanation of the error
    """

    def __init__(self, num, msg):
        """Create a new NotASafePrimeError exception
        """
        self.num = num
        ParameterError.__init__(self, msg)


class NotAGeneratorError(ParameterError):
    """
    Given number is not a generator.
    
    Exception raised when a number claimed to be a generator for an ElGamal 
    scheme with a certain prime is not really a generator. 

    Attributes:
        prime::int  -- the prime defining the Z_{p}^{*} cyclic group of which 
                       a generator was sought
        num::int    -- the given number
        msg::string -- explanation of the error
    """

    def __init__(self, prime, num, msg):
        """Create a new NotAGeneratorError exception
        """
        self.prime = prime
        self.num = num
        ParameterError.__init__(self, msg)



class EGCSUnconstructedStateError(Exception):
    """
    Raised when an EGCryptoSystem instance is improperly constructed and used.
    
    This exception is raised when an EGCryptoSystem instance that was not 
    properly constructed is accessed.
    
    EGCryptoSystem may not be constructed through the __init__ constructor. It 
    must be created through one of its factory class methods, such as new() or
    load(nbits, prime, generator).
    """
    
    def __str__(self):
        return self.msg

    def __init__(self):
        """
        Create a new EGCSUnconstructedStateError exception.
        """
        self.msg = "Attempted to use an improperly constructed cryptosystem. " \
                   "EGCryptoSystem objects must be obtained through the " \
                   "class' factory methods, such as new() or load(nbits, " \
                   "prime, generator)."



class InvalidPloneVoteCryptoFileError(ParameterError):
    """
    The given file is not a valid PloneVoteCryptoLib file of the expected type. 
    
    This exception should be raised when an incorrectly formated XML file is 
    given to the functions or methods for decoding stored PVCL information, 
    such as: cryptosystem instances, public keys, private keys and encrypted 
    cypertexts.

    Attributes:
        filename::string    -- the name of the invalid file
        msg::string         -- explanation of the error
    """

    def __init__(self, filename, msg):
        """Create a new InvalidPloneVoteCryptoFileError exception
        """
        self.filename = filename
        ParameterError.__init__(self, msg)


class IncompatibleCiphertextError(ParameterError):
    """
    Signals an attempt to decrypt a ciphertext with an incompatible private key.
    
    This exception should be raised when attempting to decrypt a ciphertext 
    (or create a partial decryption) with a private key that is not correct for 
    said ciphertext. It may also be raised when attempting to re-encrypt a 
    ciphertext with a different public key than the one originally used for 
    encrypting it.

    Attributes:
        msg::string         -- explanation of the error
    """

    def __init__(self, msg):
        """Create a new IncompatibleCiphertextError exception
        """
        ParameterError.__init__(self, msg)


# ============================================================================
# Exceptions used by Threshold.*
# ============================================================================


class ThresholdEncryptionSetUpStateError(Exception):
    """
    Raised when a ThresholdEncryptionSetUp operation is called when the 
    instance is in an inappropriate state.
    
    Common examples:
        - generate_commitment called without having registered all the 
          trustees' public keys.
        - get_fingerprint called without having registered all the trustees' 
          commitments.
        - generate_threshold_keypair called without having registered all the 
          trustees' commitments.                
    """
    
    def __str__(self):
        return self.msg

    def __init__(self, msg):
        """
        Create a new ThresholdEncryptionSetUpStateError exception.
        """
        self.msg = msg


class IncompatibleCommitmentError(Exception):
    """
    Raised when ThresholdEncryptionSetUp.add_trustee_commitment is given a 
    ThresholdEncryptionCommitment that is not compatible with the current 
    ThresholdEncryptionSetUp instance. 
    (ie. has a different number of trustees)
    """
    
    def __str__(self):
        return self.msg

    def __init__(self, msg):
        """
        Create a new IncompatibleCommitmentError exception.
        """
        self.msg = msg


class InvalidCommitmentError(ElectionSecurityError):
    """
    Raised when a ThresholdEncryptionCommitment is detected to be invalid.
    
    For example, when it is found that a partial private key given in the 
    commitment is not consistent with its public coefficients.
    
    This is an election security error. If raised, the election process may 
    only safely continue if the detected invalid commitment is replaced with a 
    correct one and threshold public and private keys are generated again from 
    scratch.
    
    Attributes:
        trustee::int    -- The number of the trustee to which the invalid 
                           commitment is associated.
        commitment::ThresholdEncryptionCommitment   -- The invalid commitment.
    """

    def __init__(self, trustee, commitment, msg):
        """
        Create a new ThresholdEncryptionSetUpStateError exception.
        """
        ElectionSecurityError.__init__(self, msg)
        self.trustee = trustee
        self.commitment = commitment


# ============================================================================
# Exceptions used by Mixnet.*
# ============================================================================


class IncompatibleReencryptionInfoError(ParameterError):
    """
    Signals an attempt to operate on incompatible CiphertextReencryptionInfo 
    objects.

    Attributes:
        msg::string         -- explanation of the error
    """

    def __init__(self, msg):
        """Create a new IncompatibleReencryptionInfoError exception
        """
        ParameterError.__init__(self, msg)


class IncompatibleCiphertextCollectionError(ParameterError):
    """
    Signals an attempt to operate on incompatible CiphertextCollection objects.

    Attributes:
        msg::string         -- explanation of the error
    """

    def __init__(self, msg):
        """Create a new IncompatibleCiphertextCollectionError exception
        """
        ParameterError.__init__(self, msg)
        
class IncompatibleCiphertextCollectionMappingError(ParameterError):
    """
    Signals an attempt to operate on incompatible CiphertextCollectionMapping 
    objects.

    Attributes:
        msg::string         -- explanation of the error
    """

    def __init__(self, msg):
        """Create a new IncompatibleCiphertextCollectionMappingError exception
        """
        ParameterError.__init__(self, msg)
        
class InvalidCiphertextCollectionMappingError(ParameterError):
    """
    Signals the use of an invalid CiphertextCollectionMapping object, when a 
    valid mapping between two CiphertextCollection objects was expected.

    Attributes:
        msg::string         -- explanation of the error
    """

    def __init__(self, msg):
        """Create a new InvalidCiphertextCollectionMappingError exception
        """
        ParameterError.__init__(self, msg)
        
class InvalidShuffilingProofError(ParameterError):
    """
    Signals the use of an invalid ShuffilingProof object.

    Attributes:
        msg::string         -- explanation of the error
    """

    def __init__(self, msg):
        """Create a new InvalidShuffilingProofError exception
        """
        ParameterError.__init__(self, msg)
