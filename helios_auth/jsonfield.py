"""
taken from

http://www.djangosnippets.org/snippets/377/
"""

import datetime, json
from django.db import models
from django.db.models import signals
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder


class JSONField(models.TextField):
    """
    JSONField is a generic textfield that neatly serializes/unserializes
    JSON objects seamlessly.
    
    deserialization_params added on 2011-01-09 to provide additional hints at deserialization time
    """

    def __init__(self, json_type=None, deserialization_params=None, **kwargs):
        self.json_type = json_type
        self.deserialization_params = deserialization_params
        super(JSONField, self).__init__(**kwargs)

    '''
    from_db_value: Converts a value as returned by the database to a Python object. 
    It is the reverse of get_prep_value().
    '''

    def from_db_value(self, value, expression, connection):
        
        """Convert our string value to JSON after we load it from the DB"""

        if self.json_type:
            if isinstance(value, self.json_type):
                return value

        if isinstance(value, dict) or isinstance(value, list):
            return value

        if value == "" or value == None:
            return None

        try:
            parsed_value = json.loads(value)
        except:
            raise Exception("not JSON")

        if self.json_type and parsed_value:
            parsed_value = self.json_type.fromJSONDict(parsed_value, **self.deserialization_params)
                
        return parsed_value


    '''
    get_prep_value: value is the current value of the model’s attribute, 
    and the method should return data in a format that has been prepared for use 
    as a parameter in a query.
    '''

    def get_prep_value(self, value):
        """Convert our JSON object to a string before we save"""
        # if isinstance(value, str):
        #     return value

        if value == None:
            return None

        if self.json_type and isinstance(value, self.json_type):
            the_dict = value.toJSONDict()
        else:
            the_dict = value

        return json.dumps(the_dict, cls=DjangoJSONEncoder)


    ''' value_to_string: Converts obj to a string. Used to serialize the value of the field. '''

    def value_to_string(self, obj):
        # value = self.value_from_obj(obj)
        # return self.get_db_prep_value(value)        
        return self.value_from_object(obj)
        
    '''
    to_python: Converts the value into the correct Python object. 
    It acts as the reverse of value_to_string(), and is also called in clean().
    '''

    # def to_python(self, value):
    #     return super().to_python(value)