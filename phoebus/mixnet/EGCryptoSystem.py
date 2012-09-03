# -*- coding: utf-8 -*-
#
# ============================================================================
# About this file:
# ============================================================================
#
#  EGCryptoSystem.py : Basic cryptosystem class.
#
#  Used for creating and storing instances of an ElGamal cryptosystem.
#
#  Part of the PloneVote cryptographic library (PloneVoteCryptoLib)
#
#  Originally written by: Lazaro Clapp
#
#  Based on ElGamal.py from the Python Cryptography Toolkit, version 2.3
#  by A.M. Kuchling.
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

# We use pycrypto (>= 2.1.0) to generate probable primes (pseudo-primes that 
# are real primes with a high probability) and cryptographically secure random 
# numbers. Note that pycrypto < 2.1.0 uses a different (ostensibly broken) 
# random  number generator, which can't be used by PloneVoteCryptoLib.
#
# We do not directly use Crypto.PublicKey.ElGamal, because doing so would 
# require relying on methods that are not part of pycrypto's public API, and 
# thus subject to change. We need a lot of data about the internals of our
# ElGamal cryptosystem in order to implement: verification, mixing, 
# threshold-encryption, etc. This is not all publicly exposed by pycrypto. 
#
# Thus, we duplicate some of the code from ElGamal.py.

from Crypto.Util import number
# secure version of python's random:
from Crypto.Random.random import StrongRandom


# Use configuration parameters from params.py
import params

# Use some PloneVoteCryptoLib exceptions
from PVCExceptions import *

# Include support for serialization
import serialize as serialize
# ============================================================================

__all__ = ["EGCryptoSystem", "EGStub", "EGCSUnconstructedStateError"]

EGStub_serialize_structure_definition = {
    "PloneVoteCryptoSystem" : (1, 1, {  # Root element
        "name" : (1, 1, None),          # exactly 1 name element
        "description" : (1, 1, None),   # exactly 1 description element
        "CryptoSystemScheme" : (1, 1, { # 1 cryptosystem element, containing:
            "nbits" : (1, 1, None),     # exactly 1 nbits element
            "prime" : (1, 1, None),     # exactly 1 prime element
            "generator" : (1, 1, None)  # exactly 1 generator element
         })
    })
}

# ============================================================================
# Helper functions:
# ============================================================================
def _is_safe_prime(p, probability=params.FALSE_PRIME_PROBABILITY):
        """
        Test if the number p is a safe prime.
        
        A safe prime is one of the form p = 2q + 1, where q is also a prime.
        
        Arguments:
            p::long    -- Any integer.
            probability::int    -- The desired maximum probability that p 
                                   or q may be composite numbers and still be 
                                   declared prime by our (probabilistic) 
                                   primality test. (Actual probability is 
                                   lower, this is just a maximum provable bound)
        
        Returns:
            True    if p is a safe prime
            False    otherwise
        """
        # Get q (p must be odd)
        if(p % 2 == 0): 
            return False
        
        q = (p - 1)/2
        
        # q first to shortcut the most common False case
        return (number.isPrime(q, false_positive_prob=probability) 
                and
                number.isPrime(p, false_positive_prob=probability))
                

def _generate_safe_prime(nbits, probability=params.FALSE_PRIME_PROBABILITY, 
                         task_monitor=None):
        """
        Generate a safe prime of size nbits.
        
        A safe prime is one of the form p = 2q + 1, where q is also a prime. 
        The prime p used for ElGamal must be a safe prime, otherwise some 
        attacks that rely on factoring the order p - 1 of the cyclic group 
        Z_{p}^{*} may become feasible if p - 1 does not have a large prime 
        factor. (p = 2q + 1, means p - 1 = 2q, which has a large prime factor,
        namely q)
        
        Arguments:
            nbits::int    -- Bit size of the safe prime p to generate. 
                           This private method assumes that the
                           nbits parameter has already been checked to satisfy 
                           all necessary security conditions.
            probability::int    -- The desired maximum probability that p 
                                   or q may be composite numbers and still be 
                                   declared prime by our (probabilistic) 
                                   primality test. (Actual probability is 
                                   lower, this is just a maximum provable bound)
            task_monitor::TaskMonitor    -- A task monitor for the process.
        
        Returns:
            p::long        -- A safe prime.
        """
        found = False
        
        # We generate (probable) primes q of size (nbits - 1) 
        # until p = 2*q + 1 is also a prime
        while(not found):
            if(task_monitor != None): task_monitor.tick()
        
            q = number.getPrime(nbits - 1)
            p = 2*q + 1
            
            if(not number.isPrime(p, probability)):
                continue
                
            # Are we sure about q, though? (pycrypto may allow a higher 
            # probability of q being composite than what we might like)
            if(not number.isPrime(q, probability)):
                continue    # pragma: no cover (Too rare to test for)
            
            found = True
            
        # DEBUG CHECK: The prime p must be of size n=nbits, that is, in 
        # [2**(n-1),2**n] (and q must be of size nbits - 1)
        if(params.DEBUG):
            assert 2**(nbits - 1) < p < 2**(nbits), \
                    "p is not an nbits prime."
            assert 2**(nbits - 2) < q < 2**(nbits - 1), \
                    "q is not an (nbits - 1) prime"
                    
        return p


def _is_generator(p, g):
        """
        Checks whether g is a generator of the Z_{p}^{*} cyclic group.
        
        This function makes two assumptions about p:
            1) p is prime
            2) p = 2q + 1 such that q is prime 
            (i.e. p is a safe prime)
        
        Since p is prime, Z_{p}^{*} is a cyclic group of order p - 1. 
        
        We ask whether g is a generator of the group, that is, whether
        g^{p-1} = g^{2q} = 1 mod p, and g^{i} != 1 mod p \\forall i < (p-1).
        
        Algorithm explanation:
        
        g^{p-1} = 1 mod p \\forall g, by Euler's theorem and the fact that p is 
        prime.
        
        For any g, if g^{i} = 1 mod p, then g generates a cyclic subgroup 
        of Z_{p}^{*} of order i. By Lagrange's theorem, the order of a (finite) 
        subgroup must divide the order of the group. Thus:
        
        g^{i} = 1 mod p => i | (p - 1)
        
        Since p - 1 = 2q, we need only check that g^{2} != 1 mod p and 
        g^{q} != 1 mod p, since only 2 or q divide p - 1, the order of 
        Z_{p}^{*}.
        
        Should both those conditions be true, g must be a generator of 
        Z_{p}^{*}.
        
        References: I.N. Herstein pg. 35, 
                    "Handbook of Applied Cryptography" Algorithm 4.80
        
        Arguments:
            p::long    -- A safe prime.
            g::long    -- An element in Z_{p}^{*}
        
        Returns:
            True    if g is a generator of Z_{p}^{*}
            False    otherwise
        """
        if(not (1 <= g <= (p - 1))):    # g must be an element in Z_{p}^{*}
            return False
        
        q = (p - 1) / 2        # Since p = 2q + 1
        if(pow(g, 2, p) == 1):
            return False
        elif(pow(g, q, p) == 1):
            return False
        else:
            return True


def _get_generator(p, task_monitor=None):
        """
        Returns the generator of the Z_{p}^{*} cyclic group.
        
        We take random numbers in Z_{p}^{*} = [0, ..., p - 1], until one of  
        them is a generator for the group. This function assumes that p is a 
        safe prime (p = 2q + 1 with both p and q prime).
        
        See the documentation for _is_generator(p, g) for more information 
        about testing whether a number is a generator of Z_{p}^{*}.
        
        Arguments:
            p::long    -- A safe prime.
            task_monitor::TaskMonitor    -- A task monitor for the process.
        
        Returns:
            g::long    -- A generator of Z_{p}^{*}
        """        
        random = StrongRandom()
        candidate = random.randint(1, p - 1)
        if(task_monitor != None): task_monitor.tick()
        
        while(not _is_generator(p, candidate)):
            candidate = random.randint(1, p - 1)
            if(task_monitor != None): task_monitor.tick()
        
        if(params.DEBUG):
            assert pow(candidate, p - 1, p) == 1, \
                   "generator^{p-1} != 1 mod p (!) see method's " \
                   "algorithm explanation."
        
        return candidate # this is the generator
        
    
# ============================================================================        



# ============================================================================
# Classes:
# ============================================================================ 
class EGCryptoSystem:
    """
    A particular cryptosystem used for PloneVote.
    
    EGCryptoSystem represents a particular instance of an ElGamal cryptosystem 
    up to the selection of of a Z_{p}^{*} group and its corresponding generator.
    
    This class is used to instantiate compatible (private + public) key pairs. 
    That is, key pairs in which the public keys can be merged into one combined 
    public key for a threshold-encryption scheme.
    
    The crypto system used also determines the cryptographic strength of the 
    generated keys, by specifying the bit size used for all keys (aka. the 
    length of the prime p or, equivalently, the cardinality of the cyclic group)
    .
    
    EGCryptoSystem may not be constructed through the __init__ constructor. It 
    must be created through one of its factory class methods, such as new() or
    load(nbits, prime, generator).
    """
    
    _nbits = None
    _prime = None
    _generator = None
    
    _constructed = False;
        
    def get_nbits(self):
        """
        Return the number of bits used as the key size by this ElGamal instance.
        """
        if(not self._constructed): raise EGCSUnconstructedStateError()
        return self._nbits    
        
    def get_prime(self):
        """
        Return the prime p used by this ElGamal instance.
        """
        if(not self._constructed): raise EGCSUnconstructedStateError()
        return self._prime    
        
    def get_generator(self):
        """
        Return the generator used by this ElGamal instance.
        
        The generator of the Z_{p}^{*} cyclic group, where p is the same as in 
        self.get_prime().
        """
        if(not self._constructed): raise EGCSUnconstructedStateError()
        return self._generator
            
    @classmethod    
    def _verify_key_size(cls, nbits):
        """
        Checks that nbits is a valid key size.
        
        This method verifies that nbits is longer than params.MINIMUM_KEY_SIZE 
        and expressible in bytes (nbits is a multiple of eight), and throws 
        an exception otherwise.
        
        Arguments:
            nbits::int    -- The key size to test
        
        Returns:
            nbits::int    -- The same key size, if it passes the tests
            
        Throws:
            KeyLengthTooLowError    -- If nbits is smaller than 
                                       params.MINIMUM_KEY_SIZE.
            KeyLengthNonBytableError -- If nbits is not a multiple of 8.
        """
        # Check that the key size meets the minimum key size requirements
        if(nbits < params.MINIMUM_KEY_SIZE):
        
            # Throw an exception w/ an appropriate message if nbits is too small
            raise KeyLengthTooLowError(nbits, params.MINIMUM_KEY_SIZE, 
                "The given size in bits for the cryptosystem (%d bits) is too" \
                " low. For security reasons, current minimum allowed key/" \
                "cryptosystem bit size is %d bits. It is recommended that " \
                " only keys of that length or higher are generated or used. " \
                " If you must use smaller keys, you may configure " \
                "PloneVoteCryptoLib's security parameters in params.py at " \
                "your own risk." % (nbits, params.MINIMUM_KEY_SIZE))
                
        # Check that the key size is can be expressed as whole bytes (i.e. is
        # a multiple of 8)
        if(nbits % 8 != 0):
        
            raise KeyLengthNonBytableError(nbits,
                "The given size in bits for the cryptosystem (%d bits) is " \
                "not a multiple of eight. Currently, only key sizes that are " \
                "multiples of eight, and thus expressible in whole bytes, " \
                "are allowed by PloneVoteCryptoLib. Perhaps you could use %d " \
                "bit keys?" % (nbits, (nbits/8 + 1)*8) )
                
        return nbits
    
    def __eq__(self, other):
        """
        Equality (==) operator.
        """
        return (type(self) == type(other) and \
                self._nbits == other._nbits and \
                self._prime == other._prime and \
                self._generator == other._generator)
                
    def __ne__(self, other):
        """
        Inequality (!=) operator.
        """
        return not self.__eq__(other)
    
    def __init__(self):
        """
        DO NOT USE THIS CONSTRUCTOR
        
        This constructor should never be used directly. Instead, the following 
        factory methods should be considered:
        
            new()                -- Generates a new EGCryptoSystem with the 
                                   default security
            new(nbits::int)        -- Generates a new EGCryptoSystem with key size
                                   nbits
            load(nbits::int, 
                prime::int, 
                generator::int) -- Loads an EGCryptoSystem with key size nbits, 
                                   prime p and generator g. Verifies parameters.
        """
        pass
            
    @classmethod
    def new(cls, nbits=params.DEFAULT_KEY_SIZE, task_monitor=None):
        """
        Construct a new EGCryptoSystem object with an specific bit size.
        
        This generates a prime, cyclic group and generator for the ElGamal 
        cryptographic scheme, given the desired length in bits of the prime. 
        If the bit size is not given, a default is used which depends upon the 
        PloneVoteCryptoLib configuration in params.py (mainly SECURITY_LEVEL, 
        but can be override by setting CUSTOM_DEFAULT_KEY_SIZE).
        
        Arguments:
            nbits::int    -- Bit size of the prime to use for the ElGamal scheme.
                           Higher is safer but slower.
                           Must be a multiple of eight (ie. expressible in 
                           bytes).
            task_monitor::TaskMonitor    -- A Task Monitor object to monitor the 
                                           cryptosystem generation process.
                           
        Throws:
            KeyLengthTooLowError    -- If nbits is smaller than 
                                       params.MINIMUM_KEY_SIZE.
            KeyLengthNonBytableError -- If nbits is not a multiple of 8.
        """
        # Call empty class constructor
        cryptosystem = cls()
        
        # Verify the key size
        cryptosystem._nbits = cls._verify_key_size(nbits)
        
        # Generate a safe (pseudo-)prime of size _nbits
        if(task_monitor != None):
            prime_task = task_monitor.new_subtask("Generate safe prime", 
                                    percent_of_parent = 80.0)
            cryptosystem._prime = _generate_safe_prime(cryptosystem._nbits, 
                                                       task_monitor=prime_task)
            prime_task.end_task()
        else:
            cryptosystem._prime = _generate_safe_prime(cryptosystem._nbits)
            
        # Now we need the generator for the Z_{p}^{*} cyclic group
        if(task_monitor != None):
            generator_task = task_monitor.new_subtask(\
                                    "Obtain a generator for the cyclic group", 
                                    percent_of_parent = 20.0)
            cryptosystem._generator = _get_generator(cryptosystem._prime, 
                                                     generator_task)
            generator_task.end_task()
        else:
            cryptosystem._generator = _get_generator(cryptosystem._prime)
        
        # Mark the object as constructed
        cryptosystem._constructed = True
        
        # Return the EGCryptoSystem instance
        return cryptosystem
            
    @classmethod
    def load(cls, nbits, prime, generator):
        """
        Construct an EGCryptoSystem object with pre-generated parameters.
        
        This method returns a new ElGamal cryptosystem with the given bit size, 
        safe prime and generator. All three arguments are tested before the 
        cryptosystem is constructed.
        
        This constructor is intended for loading pre-generated cryptosystems, 
        such as those stored as files via EGStub.
        
        Arguments:
            nbits::int    -- Bit size of the prime to use for the ElGamal scheme. 
                           Must be a multiple of eight (ie. expressible in 
                           bytes).
            prime::long -- A nbits-long safe prime 
                           (that is (prime-1)/2 is also prime).
            generator:long -- A generator of the Z_{p}^{*} cyclic group.
                           
        Throws:
            KeyLengthTooLowError    -- If nbits is smaller than 
                                       params.MINIMUM_KEY_SIZE.
            KeyLengthNonBytableError -- If nbits is not a multiple of 8.
            KeyLengthMismatch        -- If the prime is not an nbits long number.
            NotASafePrimeError        -- If prime is not a safe prime
            NotAGeneratorError        -- If generator is not a generator of 
                                       Z_{p}^{*}
        """
        
        # Call empty class constructor
        cryptosystem = cls()
        
        # Verify the key size
        cryptosystem._nbits = cls._verify_key_size(nbits)
        
        # Verify the size of prime
        if(not (2**(nbits - 1) <= prime <= 2**nbits)):
            raise KeyLengthMismatch(
                    "The number given as the cryptosystem's prime (%d) is " \
                    "not of the specified cryptosystem's bit size (%d)." \
                    % (prime, nbits))
        
        # Verify that prime is a safe prime
        prob = params.FALSE_PRIME_PROBABILITY_ON_VERIFICATION
        if(_is_safe_prime(prime, prob)):
            cryptosystem._prime = prime
        else:
            raise NotASafePrimeError(prime,
                "The number given as prime p for the ElGamal cryptosystem " \
                "is not a safe prime.")
            
        # Verify the generator
        if(_is_generator(prime, generator)):
            cryptosystem._generator = generator
        else:
            raise NotAGeneratorError(prime, generator,
                "The number given as generator g for the ElGamal " \
                "cryptosystem is not a generator of Z_{p}^{*}.")
        
        # Mark the object as constructed
        cryptosystem._constructed = True
        
        # Return the EGCryptoSystem instance
        return cryptosystem
        
    def to_stub(self, name, description):
        """
        Creates an EGStub object from the current cryptosystem.
        
        Arguments:
            name::string    -- Short name of the cryptosystem.
            description::string    -- Description of the cryptosystem.
        """
        if(not self._constructed): raise EGCSUnconstructedStateError()
        return EGStub(name, description, self._nbits, self._prime, 
                      self._generator)
    
    def to_dom_element(self, doc):
        """
        Returns a CryptoSystemScheme XML/DOM element for this cryptosystem.
        
        The CryptoSystemScheme XML element is embedded into the private and 
        public key XML files and describes only the fundamental values (nbits, 
        prime and generator) of the cryptosystem, omitting the name and 
        description.
        
        Note that if you wish to save the cryptosystem or cryptosystem stub to 
        a file or some other permanent storage, it is far more likely that you 
        want to use the EGStub.to_xml method (or better yet, to_file) rather 
        than this one.
        
        Arguments:
            doc::xml.dom.minidom.Document    -- The document of which the 
                      CryptoSystemScheme XML element will eventually form part. 
                      Note that this method does not append the node to the 
                      document, it just returns it as an object.
        
        Returns:
            node::xml.dom.minidom.Node
        """
        string = "This should never be printed. - EGCryptoSystem.py"
        return self.to_stub(string, string).to_dom_element(doc)
        
    def to_file(self, name, description, filename):
        """
        Saves the current cryptosystem to a file.
        
        The file can then be loaded from this class with the load_from_file 
        class method, or as an EGStub to avoid the overhead of verifying the 
        cryptosystem parameters.
        
        A name and description must be stored within the file.
        """
        self.to_stub(name, description).to_file(filename)
        
    @classmethod
    def from_file(self, filename):
        """
        Loads an instance of the cryptosystem from the given file.
        
        This verifies the stored cryptosystem's parameters for correctness and 
        security. May throw any exception thrown by .load() if the stored 
        parameters are invalid.
        """
        return EGStub.from_file(filename).to_cryptosystem()
        
    def new_key_pair(self):
        """
        Generate a new key pair within this cryptosystem
        
        Returns:
            key_pair::KeyPair    -- A new key pair using the current 
                                   cryptosystem.
        """
        from KeyPair import KeyPair # avoids circular imports
        return KeyPair(self)
    

class EGStub:
    """
    Represents an unverified set of parameters for an ElGamal scheme.
    
    EGStub is used to record, store and examine the parameters of an ElGamal 
    cryptosystem in a way that requires no verification overhead.
    
    EGStub can be used to store and load EGCryptoSystem instances from and to 
    .pvcryptosys XML files, as well as examine the parameters described in 
    those files. ElGamal parameters are verified for correctness and strength 
    only when the EGStub is unpacked into an EGCryptoSystem instance that can 
    be used to produce a key pair.
    
    Attributes:
        name::string    -- Short name of the stored/to_store cryptosystem.
        description::string    -- Description of the cryptosystem.
        nbits::int        -- Bit size to use for the cryptosystem.
        prime::long     -- The nbits-long safe prime.
        generator:long     -- The generator.
    """
    
    def is_secure(self):
        """
        Checks whether the cryptosystem described by the EGStub is secure.
        
        This only verifies that the length in bits given is a multiple of eight 
        and at least as large as the minimum size set for the system.
        """
        return (self.nbits % 8 == 0) and (self.nbits >= params.MINIMUM_KEY_SIZE)
    
    def __init__(self, name, description, nbits, prime, generator):
        """
        Creates a new EGStub with the given parameters.
        """
        self.name = name
        self.description = description
        self.nbits = nbits
        self.prime = prime
        self.generator = generator
    
    def to_cryptosystem(self):
        """
        Unpack the EGStub into a full cryptosystem.
        
        This method obtains an EGCryptoSystem from the current EGStub instance, 
        verifying the correctness and security of the parameters in the 
        process. The resulting EGCryptoSystem can then be used to generate a 
        private and public key pair to use for encryption/decryption.
        
        Returns:
            cryptosys::EGCryptoSystem    -- A verified cryptosystem using the 
                                           security parameters described by 
                                           this stub
                           
        Throws:
            KeyLengthTooLowError    -- If nbits is smaller than 
                                       params.MINIMUM_KEY_SIZE.
            KeyLengthNonBytableError -- If nbits is not a multiple of 8.
            KeyLengthMismatch        -- If the prime is not an nbits long number.
            NotASafePrimeError        -- If prime is not a safe prime
            NotAGeneratorError        -- If generator is not a generator of 
                                       Z_{p}^{*}
        """
        return EGCryptoSystem.load(self.nbits, self.prime, self.generator)
    
    # OBSOLETE: Remove as soon as all consuming classes through PVCL have been 
    # upgraded to use the serialize API
    def to_dom_element(self, doc): # pragma: no cover
        """
        Returns a CryptoSystemScheme XML/DOM element for this cryptosystem stub.
        
        The CryptoSystemScheme XML element is embedded into the private and 
        public key XML files and describes only the fundamental values (nbits, 
        prime and generator) of the cryptosystem, omitting the name and 
        description.
        
        Note that if you wish to save the cryptosystem or cryptosystem stub to 
        a file or some other permanent storage, it is far more likely that you 
        want to use the to_xml method (or better yet, to_file) rather than this 
        one.
        
        Arguments:
            doc::xml.dom.minidom.Document    -- The document of which the 
                      CryptoSystemScheme XML element will eventually form part. 
                      Note that this method does not append the node to the 
                      document, it just returns it as an object.
        
        Returns:
            node::xml.dom.minidom.Node
        """
        cs_scheme_element = doc.createElement("CryptoSystemScheme")
        
        nbits_element = doc.createElement("nbits")
        nbits_element.appendChild(doc.createTextNode(str(self.nbits)))
        cs_scheme_element.appendChild(nbits_element)
        
        prime_element = doc.createElement("prime")
        prime_str = hex(self.prime)[2:]        # Remove leading '0x'
        if(prime_str[-1] == 'L'): 
            prime_str = prime_str[0:-1]        # Remove trailing 'L'
        prime_element.appendChild(doc.createTextNode(prime_str))
        cs_scheme_element.appendChild(prime_element)
        
        generator_element = doc.createElement("generator")
        generator_str = hex(self.generator)[2:]        # Remove leading '0x'
        if(generator_str[-1] == 'L'): 
            generator_str = generator_str[0:-1]        # Remove trailing 'L'
        generator_element.appendChild(doc.createTextNode(generator_str))
        cs_scheme_element.appendChild(generator_element)
        
        return cs_scheme_element
        
    def to_file(self, filename, SerializerClass=serialize.XMLSerializer):
        """
        Saves this EGStub to a file.
        
        Arguments:
            filename::string    -- The path to the file in which to store the 
                                   serialized EGStub object.
            SerializerClass::class --
                The class that provides the serialization. XMLSerializer by 
                default. Must inherit from serialize.BaseSerializer and provide 
                an adequate serialize_to_file method.
                Note that often the same class used to serialize the data must 
                be used to deserialize it.
                (see utilities/serialize.py documentation for more information)
        """
        # Create a new serializer object for the EGStub structure definition
        serializer = SerializerClass(EGStub_serialize_structure_definition)
        
        # Encode prime and generator as strings in hexadecimal representation
        prime_str = hex(self.prime)[2:]        # Remove leading '0x'
        if(prime_str[-1] == 'L'): 
            prime_str = prime_str[0:-1]        # Remove trailing 'L'
        
        generator_str = hex(self.generator)[2:]        # Remove leading '0x'
        if(generator_str[-1] == 'L'): 
            generator_str = generator_str[0:-1]        # Remove trailing 'L'
        
        # Generate a serializable data dictionary matching the definition:
        data = {
            "PloneVoteCryptoSystem" : {
                "name" : self.name,
                "description" : self.description,
                "CryptoSystemScheme" : {
                    "nbits" : str(self.nbits),
                    "prime" : prime_str,
                    "generator" : generator_str
                }
            }
        }
        
        # Use the serializer to store the data to file
        serializer.serialize_to_file(filename, data)
    
    # OBSOLETE: Remove as soon as all consuming classes through PVCL have been 
    # upgraded to use the serialize API
    @classmethod
    def parse_crytosystem_scheme_xml_node(cls, cs_scheme_element): # pragma: no cover
        """
        Parse a CryptoSystemScheme XML node.
        
        Multiple PloneVoteCryptoLib storage formats include a 
        CryptoSystemScheme node containing the details of the cryptosystem 
        instance to use. This class method parses such node and returns a 
        tuple (nbits, prime, generator).
        
        Arguments:
            cs_scheme_element    -- An DOM node pointing to a CryptoSystemScheme 
                                   XML node
        
        Throws:
            InvalidPloneVoteCryptoFileError -- If the given DOM node is not a 
                                               valid CryptoSystemScheme XML 
                                               node
        
        Returns:
            (nbits, prime, generator)::(int, long, long)
        """
        nbits_element = prime_element = generator_element = None
        
        for node in cs_scheme_element.childNodes:
            if node.nodeType == node.ELEMENT_NODE:
                if node.localName == "nbits":
                    nbits_element = node
                elif node.localName == "prime":
                    prime_element = node
                elif node.localName == "generator":
                    generator_element = node
        
        # Get nbits
        if(nbits_element == None):
            raise InvalidPloneVoteCryptoFileError(filename, 
                "The <CryptoSystemScheme> specification must include the " \
                "cryptosystem instance's key size in bits.")
                
        if(len(nbits_element.childNodes) != 1 or 
            nbits_element.childNodes[0].nodeType != \
            nbits_element.childNodes[0].TEXT_NODE):
            
            raise InvalidPloneVoteCryptoFileError(filename, 
                "The <CryptoSystemScheme> specification must include the " \
                "cryptosystem instance's key size in bits.")
        
        nbits_str = nbits_element.childNodes[0].data.strip()    # trim spaces
        nbits = int(nbits_str)
        
        # Get prime
        if(prime_element == None):
            raise InvalidPloneVoteCryptoFileError(filename, 
                "The <CryptoSystemScheme> specification must include the " \
                "cryptosystem instance's prime.")
                
        if(len(prime_element.childNodes) != 1 or 
            prime_element.childNodes[0].nodeType != \
            prime_element.childNodes[0].TEXT_NODE):
            
            raise InvalidPloneVoteCryptoFileError(filename,  
                "The <CryptoSystemScheme> specification must include the " \
                "cryptosystem instance's prime.")
        
        prime_str = prime_element.childNodes[0].data.strip()
        prime = int(prime_str, 16)    # From hexadecimal representation
        
        # Get generator
        if(generator_element == None):
            raise InvalidPloneVoteCryptoFileError(filename, 
                "The <CryptoSystemScheme> specification must include the " \
                "cryptosystem instance's generator.")
                
        if(len(generator_element.childNodes) != 1 or 
            generator_element.childNodes[0].nodeType != \
            generator_element.childNodes[0].TEXT_NODE):
            
            raise InvalidPloneVoteCryptoFileError(filename,  
                "The <CryptoSystemScheme> specification must include the " \
                "cryptosystem instance's generator.")
        
        generator_str = generator_element.childNodes[0].data.strip()
        generator = int(generator_str, 16)
        
        return (nbits, prime, generator)
        
    @classmethod
    def from_file(cls, filename, SerializerClass=serialize.XMLSerializer):
        """
        Loads an instance of EGStub from the given file.
        
        Arguments:
            filename::string    -- The name of a file containing the EGStub 
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
                                               cryptosystem file.
        """
        # Create a serializer object of class SerializerClass with the 
        # structure definition for EGStub
        serializer = SerializerClass(EGStub_serialize_structure_definition)
        
        # Deserialize the EGStub instance from file
        try:
            data = serializer.deserialize_from_file(filename)
        except serialize.InvalidSerializeDataError, e:
            # Convert the exception to an InvalidPloneVoteCryptoFileError
            raise InvalidPloneVoteCryptoFileError(filename, \
                "File \"%s\" does not contain a valid cryptosystem. The " \
                "following error occurred while trying to deserialize the " \
                "file contents: %s" % (filename, str(e)))
        
        name = data["PloneVoteCryptoSystem"]["name"]
        description = data["PloneVoteCryptoSystem"]["description"]
        
        inner_elems = data["PloneVoteCryptoSystem"]["CryptoSystemScheme"]
        try:
            nbits = int(inner_elems["nbits"])
            prime = int(inner_elems["prime"], 16)
            generator = int(inner_elems["generator"], 16)
        except ValueError, e:
            raise InvalidPloneVoteCryptoFileError(filename, \
                "File \"%s\" does not contain a valid cryptosystem. The " \
                "stored values for nbits, prime and generator are not all " \
                "valid integers in the expected format. Inner error message: " \
                "%s" % (filename, str(e)))
        
        # Create a new EGStub
        return cls(name, description, nbits, prime, generator)
    

# ============================================================================
