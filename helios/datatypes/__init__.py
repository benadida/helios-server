"""
The Helios datatypes are RDF datatypes that map to JSON-LD

A datatype object wraps another object and performs serialization / de-serialization
to and from that object. For example, a Helios election is treated as follows:

  helios_election = get_current_election() # returns a helios.models.Election object
  
  # dispatch to the right contructor via factory pattern
  # LDObject knows about base classes like Election, Voter, CastVote, Trustee
  # and it looks for the datatype field within the wrapped object to determine
  # which LDObject subclass to dispatch to.
  ld_object = LDObject.instantiate(helios_election)

  # get some JSON-LD
  ld_object.serialize()

And when data comes in:

  # the type is the base type, Election, CastVote, Trustee, ...
  # if this is raw JSON, then this invokes the legacy LDObject parser
  # if this is JSON-LD, then it finds the right LDObject based on the declared type
  # in the JSON-LD.
  # the optional type variable is necessary for legacy objects (otherwise, what is the type?)
  # but is not necessary for full JSON-LD objects.
  LDObject.deserialize(json_string, type=...)
"""

from helios import utils
from helios.crypto import utils as cryptoutils

##
## utility function
##
def recursiveToDict(obj):
    if not obj:
        return None

    if type(obj) == list:
        return [recursiveToDict(el) for el in obj]
    else:
        return obj.toDict()

class LDObjectContainer(object):
    """
    a simple container for an LD Object.
    """
    
    @property
    def ld_object(self):
        if not hasattr(self, '_ld_object'):
            self._ld_object = LDObject.instantiate(self)

        return self._ld_object

    def toJSONDict(self):
        return self.ld_object.toDict()

    def toJSON(self):
        return self.ld_object.serialize()

    @property
    def hash(self):
        return self.ld_object.hash

class LDObject(object):
    """
    A linked-data object wraps another object and serializes it according to a particular
    data format. For example, a legacy election LDObject instance will wrap an Election object
    and serialize its fields according to the specs for that version.

    To accomodate old JSON types, we allow  classes to do basically whatever they want,
    or to let this base class serialize pure JSON thingies, without the JSON-LD.
    """

    # whether or not to add JSON-LD things
    USE_JSON_LD = True

    # fields to serialize
    FIELDS = []

    # structured fields
    STRUCTURED_FIELDS = {}

    def __init__(self, wrapped_obj):
        self.wrapped_obj = wrapped_obj
        self.structured_fields = {}

    @classmethod
    def get_class(cls, datatype):
        # parse datatype string "v31/Election" --> from v31 import Election
        parsed_datatype = datatype.split("/")

        # get the module
        dynamic_module = __import__(".".join(parsed_datatype[:-1]), globals(), locals(), [], level=-1)

        # go down the attributes to get to the class
        dynamic_ptr = dynamic_module
        for attr in parsed_datatype[1:]:
            dynamic_ptr = getattr(dynamic_ptr, attr)
        dynamic_cls = dynamic_ptr
        
        return dynamic_cls
        
    @classmethod
    def instantiate(cls, obj, datatype=None):
        if hasattr(obj, 'datatype') and not datatype:
            datatype = getattr(obj, 'datatype')

        if not datatype:
            raise Exception("no datatype found")

        # nulls
        if not obj:
            return None

        # array
        if isArray(datatype):
            return [cls.instantiate(el, datatype = datatype.element_type) for el in obj]

        # the class
        dynamic_cls = cls.get_class(datatype)

        # instantiate it
        return_obj = dynamic_cls(obj)

        # go through the subfields and instantiate them too
        for subfield_name, subfield_type in dynamic_cls.STRUCTURED_FIELDS.iteritems():
            return_obj.structured_fields[subfield_name] = cls.instantiate(getattr(return_obj.wrapped_obj, subfield_name), datatype = subfield_type)

        return return_obj

    def set_from_args(self, **kwargs):
        for f in self.FIELDS:
            if kwargs.has_key(f):
                new_val = self.process_value_in(f, kwargs[f])
                setattr(self.wrapped_obj, f, new_val)
            else:
                setattr(self.wrapped_obj, f, None)
        
    def serialize(self):
        return utils.to_json(self.toDict())
    
    def toDict(self, alternate_fields=None):
        val = {}
        for f in (alternate_fields or self.FIELDS):
            # is it a structured subfield?
            if self.structured_fields.has_key(f):
                val[f] = recursiveToDict(self.structured_fields[f])
            else:
                val[f] = self.process_value_out(f, getattr(self.wrapped_obj, f))
        return val

    @classmethod
    def fromDict(cls, d):
        raise Exception("not a good idea yet")

        # go through the keys and fix them
        new_d = {}
        for k in d.keys():
            new_d[str(k)] = d[k]
      
        return cls(**new_d)

    @property
    def hash(self):
        s = self.serialize()
        return cryptoutils.hash_b64(s)
    
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
  

class ArrayOfObjects(LDObject):
    """
    If one type has, as a subtype, an array of things, then this is the structured field used
    """

    def __init__(self, wrapped_array, item_type):
        self.item_type = item_type
        self.items = [LDObject.instantiate(wrapped_item, item_type) for wrapped_item in wrapped_array]
    
    def toDict(self):
        return [item.serialize() for item in self.items]

class arrayOf(object):
    """
    a wrapper for the construtor of the array
    returns the constructor
    """
    def __init__(self, element_type):
        self.element_type = element_type

def isArray(field_type):
    return type(field_type) == arrayOf
