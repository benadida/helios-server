import os
import random

from rollbar.lib import build_key_matcher, text
from rollbar.lib.transforms import Transform


class ScrubTransform(Transform):
    def __init__(self, suffixes=None, redact_char='*', randomize_len=True):
        super(ScrubTransform, self).__init__()
        self.suffix_matcher = build_key_matcher(suffixes, type='suffix')
        self.redact_char = redact_char
        self.randomize_len = randomize_len

    def in_scrub_fields(self, key):
        return self.suffix_matcher(key)

    def redact(self, val):
        if self.randomize_len:
            _len = random.randint(3, 20)
        else:
            try:
                _len = len(val)
            except:
                _len = len(text(val))

        return self.redact_char * _len

    def default(self, o, key=None):
        if self.in_scrub_fields(key):
            return self.redact(o)

        return o


__all__ = ['ScrubTransform']
