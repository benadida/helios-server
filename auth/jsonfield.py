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

        if value == "":
            return None

        try:
            if isinstance(value, basestring):
                parsed_value = json.loads(value)
                if self.json_type and parsed_value:
                    parsed_value = self.json_type.fromJSONDict(parsed_value)

                return parsed_value
        except ValueError:
            pass

        return value

    def get_db_prep_save(self, value):
        """Convert our JSON object to a string before we save"""

        if value == "" or value == None:
            return None

        if value and (self.json_type or hasattr(value, 'toJSONDict')):
            value = value.toJSONDict()

        # if isinstance(value, dict):
        value = json.dumps(value, cls=DjangoJSONEncoder)

        return super(JSONField, self).get_db_prep_save(value)
