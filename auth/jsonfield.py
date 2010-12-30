"""
taken from

http://www.djangosnippets.org/snippets/377/
"""

import datetime
from django.db import models
from django.db.models import signals
from django.conf import settings
from django.utils import simplejson as json
from django.core.serializers.json import DjangoJSONEncoder

class JSONField(models.TextField):
    """JSONField is a generic textfield that neatly serializes/unserializes
    JSON objects seamlessly"""

    # Used so to_python() is called
    __metaclass__ = models.SubfieldBase

    def __init__(self, json_type=None, **kwargs):
        self.json_type = json_type
        super(JSONField, self).__init__(**kwargs)

    def to_python(self, value):
        """Convert our string value to JSON after we load it from the DB"""

        # must handle the case where the value is already ready
        if self.json_type:
            if isinstance(value, self.json_type):
                return value
        else:
            if isinstance(value, dict) or isinstance(value, list):
                return value

        if value == "" or value == None:
            return None

        parsed_value = json.loads(value)
        if self.json_type and parsed_value:
            parsed_value = self.json_type.fromJSONDict(parsed_value)
                
        return parsed_value

    # we should never look up by JSON field anyways.
    # def get_prep_lookup(self, lookup_type, value)

    def get_prep_value(self, value):
        """Convert our JSON object to a string before we save"""
        if isinstance(value, basestring):
            return value

        if value == None:
            return None

        if self.json_type or hasattr(value,'toJSONDict'):
            the_dict = value.toJSONDict()
        else:
            the_dict = value

        return json.dumps(the_dict, cls=DjangoJSONEncoder)


    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_db_prep_value(value)        

##
## for schema migration, we have to tell South about JSONField
## basically that it's the same as its parent class
##
from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^auth\.jsonfield\.JSONField"])
