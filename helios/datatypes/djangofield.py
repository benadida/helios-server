"""
taken from

http://www.djangosnippets.org/snippets/377/

and adapted to LDObject
"""

from django.db import models

from helios import utils
from . import LDObject


class LDObjectField(models.TextField):
    """
    LDObject is a generic textfield that neatly serializes/unserializes
    JSON objects seamlessly.
    
    deserialization_params added on 2011-01-09 to provide additional hints at deserialization time
    """

    def __init__(self, type_hint=None, **kwargs):
        self.type_hint = type_hint
        super(LDObjectField, self).__init__(**kwargs)

    def to_python(self, value):
        """Convert our string value to LDObject after we load it from the DB"""

        # did we already convert this?
        if not isinstance(value, str):
            return value

        return self.from_db_value(value)

    # noinspection PyUnusedLocal
    def from_db_value(self, value, *args, **kwargs):
        # in some cases, we're loading an existing array or dict,
        # from_json takes care of this duality
        parsed_value = utils.from_json(value)
        if parsed_value is None:
            return None

        # we give the wrapped object back because we're not dealing with serialization types
        return_val = LDObject.fromDict(parsed_value, type_hint=self.type_hint).wrapped_obj
        return return_val

    def get_prep_value(self, value):
        """Convert our JSON object to a string before we save"""
        if isinstance(value, str):
            return value

        if value is None:
            return None

        # instantiate the proper LDObject to dump it appropriately
        ld_object = LDObject.instantiate(value, datatype=self.type_hint)
        return ld_object.serialize()

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_db_prep_value(value, None)
