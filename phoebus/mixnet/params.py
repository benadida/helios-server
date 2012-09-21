# -*- coding: utf-8 -*-
#
#  params.py : Configuration parameters and constants used by PloneVoteCryptoLib
#
#  Modify the values of the constants of this file under "Basic parameters" and
#  "Advanced parameters" to easily customize PloneVoteCrypto behavior.
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
# Imports, skip this section to "Basic parameters"
# ============================================================================
from Enumerate import Enumerate


# ============================================================================
# Basic parameters
# ============================================================================

# Is this a debug build?
# This will trigger additional verifications at the cost of speed.
DEBUG = False

# What level of security we should use?
# This affects derived parameters, the higher the security level, the stronger
# the security parameters that are used, but the computations become slower.

SECURITY_LEVELS_ENUM = Enumerate(       # Do not modify this enumeration
        'INSECURE',  # Do not use except for tests, broken security.
        'LOWEST',    # Expected to be breakable NOW
                     #      (but only with high computational resources).
        'LOW',       # Likely safe now, but considered unsafe past 2030.
        'NORMAL',    # The recommended default.
        'HIGH',      # A bit above the recommended parameters, just to be safe
        'HIGHEST',   # Tries to follow NIST key management guidelines for
                     #      256bit-symmetric equivalent key strength.
        'OVERKILL')  # Wastes CPU and storage space.

SECURITY_LEVEL = SECURITY_LEVELS_ENUM.NORMAL



# ============================================================================
# Expert parameters
# ============================================================================

# Modify only if you understand the cryptography involved

# Key-size to use if *not specified by user*
# (never use anything lower than 1024 bits)
# If None, default key-size will be selected based on SECURITY_LEVEL
CUSTOM_DEFAULT_KEY_SIZE = None

# Minimum key-size allowed *when specified by user*
# (never use anything lower than 1024 bits)
# If None, minimum key-size will be selected based on SECURITY_LEVEL
CUSTOM_MINIMUM_KEY_SIZE = None

# The probability that we select a composite number instead of a prime when
# setting up the cryptosystem.
# If None, false prime probability will be selected based on SECURITY_LEVEL
CUSTOM_FALSE_PRIME_PROBABILITY = None

# The integer security parameter used by the shuffling/mixing proof.
# (see ShufflingProof comments)
# If None, the security parameter will be selected based on SECURITY_LEVEL
CUSTOM_SHUFFLING_PROOF_SECURITY_PARAMETER = None


# ============================================================================
# Generated parameters
# ============================================================================

# DO NOT MODIFY
# (unless you consider yourself a PloneVoteCryptoLib developer, of course)

if(CUSTOM_MINIMUM_KEY_SIZE != None):
    MINIMUM_KEY_SIZE = CUSTOM_MINIMUM_KEY_SIZE
else:
    MINIMUM_KEY_SIZE = {
                        SECURITY_LEVELS_ENUM.INSECURE : 0,
                        SECURITY_LEVELS_ENUM.LOWEST : 1024,
                        SECURITY_LEVELS_ENUM.LOW : 2048,
                        SECURITY_LEVELS_ENUM.NORMAL : 2048,
                        SECURITY_LEVELS_ENUM.HIGH : 3072,
                        SECURITY_LEVELS_ENUM.HIGHEST : 4096,
                        SECURITY_LEVELS_ENUM.OVERKILL : 8192,
                        }[SECURITY_LEVEL]

if(CUSTOM_DEFAULT_KEY_SIZE != None):
    DEFAULT_KEY_SIZE = CUSTOM_DEFAULT_KEY_SIZE
else:
    DEFAULT_KEY_SIZE = {
                        SECURITY_LEVELS_ENUM.INSECURE : 128,
                        SECURITY_LEVELS_ENUM.LOWEST : 1024,
                        SECURITY_LEVELS_ENUM.LOW : 2048,
                        SECURITY_LEVELS_ENUM.NORMAL : 4096,
                        SECURITY_LEVELS_ENUM.HIGH : 8192,
                        SECURITY_LEVELS_ENUM.HIGHEST : 15360, # http://csrc.nist.gov/publications/nistpubs/800-57/sp800-57-Part1-revised2_Mar08-2007.pdf
                        SECURITY_LEVELS_ENUM.OVERKILL : 65536,
                        }[SECURITY_LEVEL]
if(DEFAULT_KEY_SIZE < MINIMUM_KEY_SIZE):
    print "Warning: Configuration error in params.py, the default key size " \
          "(%d) is less than the minimum key size (%d), check " \
          "CUSTOM_DEFAULT_KEY_SIZE and CUSTOM_MINIMUM_KEY_SIZE. The default " \
          "key size will be set to the minimum key size value." %  \
          (DEFAULT_KEY_SIZE, MINIMUM_KEY_SIZE)
    DEFAULT_KEY_SIZE = MINIMUM_KEY_SIZE

if(CUSTOM_FALSE_PRIME_PROBABILITY != None):
    FALSE_PRIME_PROBABILITY = CUSTOM_FALSE_PRIME_PROBABILITY
else:
    FALSE_PRIME_PROBABILITY = {
                        SECURITY_LEVELS_ENUM.INSECURE : 1e-6,
                        SECURITY_LEVELS_ENUM.LOWEST : 1e-6,
                        SECURITY_LEVELS_ENUM.LOW : 1e-6,
                        SECURITY_LEVELS_ENUM.NORMAL : 2**(-128),
                        SECURITY_LEVELS_ENUM.HIGH : 2**(-256),
                        SECURITY_LEVELS_ENUM.HIGHEST : 2**(-256),
                        SECURITY_LEVELS_ENUM.OVERKILL : 2**(-512),
                        }[SECURITY_LEVEL]

# Used when a pre-generated cryptosystem is loaded
# Much lower than FALSE_PRIME_PROBABILITY for performance reasons, but still
# high enough to detect most accidental corruptions or surreptitious
# alterations of cryptosystem or key files.
FALSE_PRIME_PROBABILITY_ON_VERIFICATION = {
                        SECURITY_LEVELS_ENUM.INSECURE : 1, #No verification
                        SECURITY_LEVELS_ENUM.LOWEST : 1e-3,
                        SECURITY_LEVELS_ENUM.LOW : 1e-3,
                        SECURITY_LEVELS_ENUM.NORMAL : 1e-4,
                        SECURITY_LEVELS_ENUM.HIGH : 1e-4,
                        SECURITY_LEVELS_ENUM.HIGHEST : 1e-6,
                        SECURITY_LEVELS_ENUM.OVERKILL : 2**(-256),
                        }[SECURITY_LEVEL]

if(CUSTOM_SHUFFLING_PROOF_SECURITY_PARAMETER != None):
    SHUFFLING_PROOF_SECURITY_PARAMETER = \
        CUSTOM_SHUFFLING_PROOF_SECURITY_PARAMETER
else:
    SHUFFLING_PROOF_SECURITY_PARAMETER = {
                        SECURITY_LEVELS_ENUM.INSECURE : 8,
                        SECURITY_LEVELS_ENUM.LOWEST : 100,
                        SECURITY_LEVELS_ENUM.LOW : 100,
                        SECURITY_LEVELS_ENUM.NORMAL : 128,
                        SECURITY_LEVELS_ENUM.HIGH : 160,
                        SECURITY_LEVELS_ENUM.HIGHEST : 200,
                        SECURITY_LEVELS_ENUM.OVERKILL : 256,
                        }[SECURITY_LEVEL]

