import collections
import logging

from rollbar.lib import binary_type, iteritems, string_types, circular_reference_label

CIRCULAR = -1
DEFAULT = 0
MAPPING = 1
TUPLE = 2
NAMEDTUPLE = 3
LIST = 4
SET = 5
STRING = 6

log = logging.getLogger(__name__)


def _noop_circular(a, **kw):
    return circular_reference_label(a, ref_key=kw.get('ref_key'))


def _noop(a, **_):
    return a


def _noop_tuple(a, **_):
    return tuple(a)


def _noop_namedtuple(a, **_):
    return a._make(a)


def _noop_list(a, **_):
    return list(a)


def _noop_set(a, **_):
    return set(a)


def _noop_mapping(a, **_):
    return dict(a)


_default_handlers = {
    CIRCULAR: _noop_circular,
    DEFAULT: _noop,
    STRING: _noop,
    TUPLE: _noop_tuple,
    NAMEDTUPLE: _noop_namedtuple,
    LIST: _noop_list,
    SET: _noop_set,
    MAPPING: _noop_mapping,
}


def get_type(obj):
    if isinstance(obj, (string_types, binary_type)):
        return STRING

    if isinstance(obj, collections.Mapping):
        return MAPPING

    if isinstance(obj, tuple):
        if hasattr(obj, '_fields'):
            return NAMEDTUPLE

        return TUPLE

    if isinstance(obj, set):
        return SET

    if isinstance(obj, collections.Sequence):
        return LIST

    return DEFAULT


def traverse(obj,
             key=(),
             string_handler=_default_handlers[STRING],
             tuple_handler=_default_handlers[TUPLE],
             namedtuple_handler=_default_handlers[NAMEDTUPLE],
             list_handler=_default_handlers[LIST],
             set_handler=_default_handlers[SET],
             mapping_handler=_default_handlers[MAPPING],
             default_handler=_default_handlers[DEFAULT],
             circular_reference_handler=_default_handlers[CIRCULAR],
             allowed_circular_reference_types=None,
             memo=None,
             **custom_handlers):

    memo = memo or {}
    obj_id = id(obj)
    obj_type = get_type(obj)

    ref_key = memo.get(obj_id)
    if ref_key:
        if not allowed_circular_reference_types or not isinstance(obj, allowed_circular_reference_types):
            return circular_reference_handler(obj, key=key, ref_key=ref_key)

    memo[obj_id] = key

    kw = {
        'string_handler': string_handler,
        'tuple_handler': tuple_handler,
        'namedtuple_handler': namedtuple_handler,
        'list_handler': list_handler,
        'set_handler': set_handler,
        'mapping_handler': mapping_handler,
        'default_handler': default_handler,
        'circular_reference_handler': circular_reference_handler,
        'allowed_circular_reference_types': allowed_circular_reference_types,
        'memo': memo
    }
    kw.update(custom_handlers)

    try:
        if obj_type is STRING:
            return string_handler(obj, key=key)
        elif obj_type is TUPLE:
            return tuple_handler(tuple(traverse(elem, key=key + (i,), **kw) for i, elem in enumerate(obj)), key=key)
        elif obj_type is NAMEDTUPLE:
            return namedtuple_handler(obj._make(traverse(v, key=key + (k,), **kw) for k, v in iteritems(obj._asdict())), key=key)
        elif obj_type is LIST:
            return list_handler(list(traverse(elem, key=key + (i,), **kw) for i, elem in enumerate(obj)), key=key)
        elif obj_type is SET:
            return set_handler(set(traverse(elem, key=key + (i,), **kw) for i, elem in enumerate(obj)), key=key)
        elif obj_type is MAPPING:
            return mapping_handler(dict((k, traverse(v, key=key + (k,), **kw)) for k, v in iteritems(obj)), key=key)
        elif obj_type is DEFAULT:
            for handler_type, handler in iteritems(custom_handlers):
                if isinstance(obj, handler_type):
                    return handler(obj, key=key)
    except:
        # use the default handler for unknown object types
        log.debug("Exception while traversing object using type-specific "
                  "handler. Switching to default handler.", exc_info=True)

    return default_handler(obj, key=key)


__all__ = ['traverse']
