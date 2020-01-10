"""
core data types
"""

from helios.datatypes import LDObject

class BigInteger(LDObject):
    """
    A big integer is an integer serialized as a string.
    We may want to b64 encode here soon.    
    """
    WRAPPED_OBJ_CLASS = int

    def toDict(self, complete=False):
        if self.wrapped_obj:
            return str(self.wrapped_obj)
        else:
            return None

    def loadDataFromDict(self, d):
        "take a string and cast it to an int -- which is a big int too"
        self.wrapped_obj = int(d)

class Timestamp(LDObject):
    def toDict(self, complete=False):
        if self.wrapped_obj:
            return str(self.wrapped_obj)
        else:
            return None
    
