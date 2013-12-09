import traceback
import datetime
import logging
import uuid
import random
import StringIO
import copy
import base64
import zipfile
import os
import tempfile
import mmap
import marshal
import itertools
import urllib

from django.db import models, transaction
from django.conf import settings
from django.core.mail import send_mail
from django.core.files import File
from django.utils.translation import ugettext_lazy as _
from django.core.validators import validate_email
from django.forms import ValidationError
from django.core.urlresolvers import reverse

from heliosauth.models import User, AUTH_SYSTEMS

from zeus.core import (numbers_hash, mix_ciphers, gamma_encoding_max,
                       gamma_decode, to_absolute_answers, to_canonical)

ELECTION_MODEL_VERSION = 1
FEATURES_REGISTRY = defaultdict(dict)


def feature(ns, *features):
    if not ns in FEATURES_REGISTRY:
        FEATURES_REGISTRY[ns] = {}

    def wrapper(func):
        for feature in features:
            if not feature in FEATURES_REGISTRY[ns]:
                FEATURES_REGISTRY[ns][feature] = []
            FEATURES_REGISTRY[ns][feature].append(func)
        @wraps(func)
        def inner(self, *args, **kwargs):
            return func(*args, **kwargs)
        return inner
    return wrapper


class FeaturesMixin(object):

    def __getattr__(self, name, *args, **kwargs):
        if name.startswith('feature_'):
            feature = name.lstrip('feature_')
            return self.check_feature(feature)
        return super(FeaturesMixin, self).__getattribute__(name, *args,
                                                           **kwargs)

    def check_feature(self, feature):
        if feature in FEATURES_REGISTRY[self.features_ns]:
            feature_checks = FEATURES_REGISTRY[self.features_ns][feature]
            return all([f(self) for f in feature_checks])
        return False

    def check_features(self, *features):
        return all([self.check_feature(f) for f in features])

    def check_features_verbose(self, *features):
        return [(f, self.check_feature(f)) for f in features]

    def list_features(self):
        return FEATURES_REGISTRY.get(self.features_ns).keys()


def election_feature(*args):
    return feature('election', *args)

def poll_feature(*args):
    return feature('poll', *args)
