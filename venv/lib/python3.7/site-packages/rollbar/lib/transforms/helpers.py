import random

from rollbar.lib import text


def redact(redact_char, randomize_len, val):
    if randomize_len:
        _len = random.randint(3, 20)
    else:
        try:
            _len = len(val)
        except:
            _len = len(text(val))

    return redact_char * _len
