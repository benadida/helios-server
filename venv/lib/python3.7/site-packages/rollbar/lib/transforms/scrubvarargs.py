import logging
import random

from rollbar.lib import build_key_matcher, text
# from rollbar.lib.transforms.helpers import redact
from rollbar.lib.transforms import Transform

log = logging.getLogger(__name__)


class ScrubVarargsTransform(Transform):
    def __init__(self, redact_char='*', randomize_len=True):
        super(ScrubVarargsTransform, self).__init__()
        self.prefix_matcher = build_key_matcher(('*',), type='prefix')
        self.redact_char = redact_char
        self.randomize_len = randomize_len

    def in_scrub_fields(self, key):
        return self.prefix_matcher(key)

    def redact(self, val):
        log.info('~*~*~ redacting val: {}'.format(val))
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

__all__ = ['ScrubVarargsTransform']
