"""
The Helios datatypes are RDF datatypes that map to JSON-LD
"""

from helios import utils

class LDObject(object):
    """
    A linked-data object wraps another object and serializes it according to a particular
    data format. For example, a legacy election LDObject instance will wrap an Election object
    and serialize its fields according to the specs for that version.

    To accomodate old JSON types, we allow  classes to override default JSON-LD fields.
    """

    # whether or not to add JSON-LD things
    USE_JSON_LD = True

    # fields to serialize
    FIELDS = []

    def set_from_args(self, **kwargs):
        for f in self.FIELDS:
            if kwargs.has_key(f):
                new_val = self.process_value_in(f, kwargs[f])
                setattr(self, f, new_val)
            else:
                setattr(self, f, None)
        
    def serialize(self):
        return utils.to_json(self.toDict())
    
    def toDict(self, alternate_fields=None):
        val = {}
        for f in (alternate_fields or self.FIELDS):
            val[f] = self.process_value_out(f, getattr(self, f))
        return val
    
    @classmethod
    def fromDict(cls, d):
        # go through the keys and fix them
        new_d = {}
        for k in d.keys():
            new_d[str(k)] = d[k]
      
        return cls(**new_d)    

    @property
    def hash(self):
        s = self.serialize()
        return utils.hash_b64(s)
    
    def process_value_in(self, field_name, field_value):
        """
        process some fields on the way into the object
        """
        if field_value == None:
            return None
      
        val = self._process_value_in(field_name, field_value)
        if val != None:
            return val
        else:
            return field_value
    
    def _process_value_in(self, field_name, field_value):
        return None

    def process_value_out(self, field_name, field_value):
        """
        process some fields on the way out of the object
        """
        if field_value == None:
            return None
      
        val = self._process_value_out(field_name, field_value)
        if val != None:
            return val
        else:
            return field_value
  
    def _process_value_out(self, field_name, field_value):
        return None
    
    def __eq__(self, other):
        if not hasattr(self, 'uuid'):
            return super(LDObject,self) == other
    
        return other != None and self.uuid == other.uuid
  
