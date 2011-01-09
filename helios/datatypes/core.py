"""
core data types
"""

from helios.datatypes import LDObject

class BigInteger(LDObject):
    """
    A big integer is an integer serialized as a string.
    We may want to b64 encode here soon.    
    """

    def toDict(self):
        if self.wrapped_obj:
            return str(self.wrapped_obj)
        else:
            return None

class Timestamp(LDObject):
    def toDict(self):
        if self.wrapped_obj:
            return str(self.wrapped_obj)
        else:
            return None
    
