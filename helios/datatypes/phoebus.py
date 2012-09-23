"""
Legacy datatypes for Phoebus stv voting platform(v3.0)
"""

from helios.datatypes import LDObject, arrayOf, DictObject, ListObject
from helios.crypto import elgamal as crypto_elgamal
from helios.workflows import homomorphic, mixnet
from helios import models


class LegacyObject(LDObject):
    WRAPPED_OBJ_CLASS = dict
    USE_JSON_LD = False

class ShortCastVote(LegacyObject):
    FIELDS = ['cast_at', 'voter_uuid', 'voter_hash', 'vote_hash']
    STRUCTURED_FIELDS = {'cast_at' : 'core/Timestamp'}


class CastVote(LegacyObject):
    FIELDS = ['vote', 'cast_at', 'voter_uuid', 'voter_hash', 'vote_hash']
    STRUCTURED_FIELDS = {
        'cast_at' : 'core/Timestamp',
        'vote' : 'phoebus/EncryptedVote'}

    @property
    def short(self):
        return self.instantiate(self.wrapped_obj, datatype='legacy/ShortCastVote')


class Election(LegacyObject):
    WRAPPED_OBJ_CLASS = models.Election
    FIELDS = ['uuid', 'questions', 'name', 'short_name', 'description',
              'voters_hash', 'openreg', 'frozen_at', 'public_key', 'cast_url',
              'use_voter_aliases', 'voting_starts_at', 'voting_ends_at',
              'workflow_type']

    STRUCTURED_FIELDS = {
        'public_key': 'legacy/EGPublicKey',
        'voting_starts_at': 'core/Timestamp',
        'voting_ends_at': 'core/Timestamp',
        'frozen_at': 'core/Timestamp'}


class Tally(LegacyObject):
    WRAPPED_OBJ_CLASS = mixnet.Tally
    FIELDS = ['tally', 'num_tallied']
    STRUCTURED_FIELDS = {
        'tally': arrayOf(arrayOf('legacy/EGCiphertext'))}

class EncryptedVote(LegacyObject):
    """
    An encrypted ballot
    """
    WRAPPED_OBJ_CLASS = mixnet.EncryptedVote
    FIELDS = ['answers', 'election_hash', 'election_uuid']
    STRUCTURED_FIELDS = {'answers': arrayOf('phoebus/EncryptedAnswer')}

    def includeRandomness(self):
        return self.instantiate(self.wrapped_obj,
                datatype='phoebus/EncryptedVoteWithRandomness')


class EncryptedVoteWithRandomness(LegacyObject):
    """
    An encrypted ballot
    """
    WRAPPED_OBJ_CLASS = mixnet.EncryptedVote
    FIELDS = ['answers', 'election_hash', 'election_uuid']
    STRUCTURED_FIELDS = {'answers':
                         arrayOf('phoebus/EncryptedAnswerWithRandomness')}


class EncryptedAnswer(LegacyObject):
    WRAPPED_OBJ_CLASS = mixnet.EncryptedAnswer
    FIELDS = ['choices', 'encryption_proof']
    STRUCTURED_FIELDS = {
        'choices': arrayOf('legacy/EGCiphertext'),
        'encryption_proof': 'core/BigInteger'}


class EncryptedAnswerWithRandomness(LegacyObject):
    FIELDS = ['choices', 'encryption_proof', 'randomness', 'answer']
    STRUCTURED_FIELDS = {
        'choices': arrayOf('legacy/EGCiphertext'),
        'encryption_proof': 'core/BigInteger',
        'randomness': arrayOf('core/BigInteger')}


class ShufflingProof(LegacyObject):
    FIELDS = ['proof']


class MixedAnswer(LegacyObject):
    WRAPPED_OBJ_CLASS = mixnet.MixedAnswer
    FIELDS = ['choice', 'index']
    STRUCTURED_FIELDS = {
        'choice': 'legacy/EGCiphertext'
    }


class MixedAnswers(LegacyObject):
    WRAPPED_OBJ_CLASS = mixnet.MixedAnswers
    FIELDS = ['answers', 'question_num']
    STRUCTURED_FIELDS = {
        'answers': arrayOf('phoebus/MixedAnswer')
    }

class Result(LegacyObject):
    WRAPPED_OBJ = list

    def loadDataFromDict(self, d, init_params={}):
        self.wrapped_obj = d

    def toDict(self, complete=False):
        return self.wrapped_obj
