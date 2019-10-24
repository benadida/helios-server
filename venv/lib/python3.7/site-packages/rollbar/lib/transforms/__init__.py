import collections

from rollbar.lib import python_major_version, binary_type, string_types, integer_types, traverse

_ALLOWED_CIRCULAR_REFERENCE_TYPES = [binary_type, bool, type(None)]

if isinstance(string_types, tuple):
    _ALLOWED_CIRCULAR_REFERENCE_TYPES.extend(string_types)
else:
    _ALLOWED_CIRCULAR_REFERENCE_TYPES.append(string_types)

if isinstance(integer_types, tuple):
    _ALLOWED_CIRCULAR_REFERENCE_TYPES.extend(integer_types)
else:
    _ALLOWED_CIRCULAR_REFERENCE_TYPES.append(integer_types)

_ALLOWED_CIRCULAR_REFERENCE_TYPES = tuple(_ALLOWED_CIRCULAR_REFERENCE_TYPES)


class Transform(object):
    def default(self, o, key=None):
        return o

    def transform_circular_reference(self, o, key=None, ref_key=None):
        # By default, we just perform a no-op for circular references.
        # Subclasses should implement this method to return whatever representation
        # for the circular reference they need.
        return self.default(o, key=key)

    def transform_tuple(self, o, key=None):
        return self.default(o, key=key)

    def transform_namedtuple(self, o, key=None):
        return self.default(o, key=key)

    def transform_list(self, o, key=None):
        return self.default(o, key=key)

    def transform_dict(self, o, key=None):
        return self.default(o, key=key)

    def transform_number(self, o, key=None):
        return self.default(o, key=key)

    def transform_py2_str(self, o, key=None):
        return self.default(o, key=key)

    def transform_py3_bytes(self, o, key=None):
        return self.default(o, key=key)

    def transform_unicode(self, o, key=None):
        return self.default(o, key=key)

    def transform_boolean(self, o, key=None):
        return self.default(o, key=key)

    def transform_custom(self, o, key=None):
        return self.default(o, key=key)



def transform(obj, transforms, key=None):
    key = key or ()

    def do_transforms(type_name, val, key=None, **kw):
        for transform in transforms:
            fn = getattr(transform, 'transform_%s' % type_name, transform.transform_custom)
            val = fn(val, key=key, **kw)

        return val

    if python_major_version() < 3:
        def string_handler(s, key=None):
            if isinstance(s, str):
                return do_transforms('py2_str', s, key=key)
            elif isinstance(s, unicode):
                return do_transforms('unicode', s, key=key)
    else:
        def string_handler(s, key=None):
            if isinstance(s, bytes):
                return do_transforms('py3_bytes', s, key=key)
            elif isinstance(s, str):
                return do_transforms('unicode', s, key=key)

    def default_handler(o, key=None):
        if isinstance(o, integer_types + (float,)):
            return do_transforms('number', o, key=key)

        if isinstance(o, bool):
            return do_transforms('boolean', o, key=key)

        return do_transforms('custom', o, key=key)

    handlers = {
        'string_handler': string_handler,
        'tuple_handler': lambda o, key=None: do_transforms('tuple', o, key=key),
        'namedtuple_handler': lambda o, key=None: do_transforms('namedtuple', o, key=key),
        'list_handler': lambda o, key=None: do_transforms('list', o, key=key),
        'set_handler': lambda o, key=None: do_transforms('set', o, key=key),
        'mapping_handler': lambda o, key=None: do_transforms('dict', o, key=key),
        'circular_reference_handler': lambda o, key=None, ref_key=None: \
            do_transforms('circular_reference', o, key=key, ref_key=ref_key),
        'default_handler': default_handler,
        'allowed_circular_reference_types': _ALLOWED_CIRCULAR_REFERENCE_TYPES
    }

    return traverse.traverse(obj, key=key, **handlers)


__all__ = ['transform', 'Transform']
