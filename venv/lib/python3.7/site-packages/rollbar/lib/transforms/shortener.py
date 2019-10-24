from array import array
import collections
import math

from rollbar.lib import integer_types, iteritems, key_in, reprlib, string_types, text
from rollbar.lib.transforms import Transform


_type_name_mapping = {
    'string': string_types,
    'long': integer_types,
    'mapping': collections.Mapping,
    'list': list,
    'tuple': tuple,
    'set': set,
    'frozenset': frozenset,
    'array': array,
    'deque': collections.deque,
    'other': None
}


class ShortenerTransform(Transform):
    def __init__(self, safe_repr=True, keys=None, **sizes):
        super(ShortenerTransform, self).__init__()
        self.safe_repr = safe_repr
        self.keys = keys
        self._repr = reprlib.Repr()

        for name, size in iteritems(sizes):
            setattr(self._repr, name, size)

    def _get_max_size(self, obj):
        for name, _type in iteritems(_type_name_mapping):
            # Special case for dicts since we are using collections.Mapping
            # to provide better type checking for dict-like objects
            if name == 'mapping':
                name = 'dict'

            if _type and isinstance(obj, _type):
                return getattr(self._repr, 'max%s' % name)

        return self._repr.maxother

    def _shorten_sequence(self, obj, max_keys):
        _len = len(obj)
        if _len <= max_keys:
            return obj

        return self._repr.repr(obj)

    def _shorten_basic(self, obj, max_len):
        val = text(obj)
        if len(val) <= max_len:
            return obj

        return self._repr.repr(val)

    def _shorten_other(self, obj):
        if obj is None:
            return None

        if isinstance(obj, float):
            if math.isinf(obj):
                return 'Infinity'

            if math.isnan(obj):
                return 'NaN'

        if self.safe_repr:
            obj = text(obj)

        return self._repr.repr(obj)

    def _shorten(self, val):
        max_size = self._get_max_size(val)

        if isinstance(val, (string_types, collections.Mapping, list, tuple, set, collections.deque)):
            return self._shorten_sequence(val, max_size)

        if isinstance(val, integer_types):
            return self._shorten_basic(val, self._repr.maxlong)

        return self._shorten_other(val)

    def _should_shorten(self, val, key):
        if not key:
            return False

        return key_in(key, self.keys)

    def default(self, o, key=None):
        if self._should_shorten(o, key):
            return self._shorten(o)

        return super(ShortenerTransform, self).default(o, key=key)


__all__ = ['ShortenerTransform']
