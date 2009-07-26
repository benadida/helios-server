#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests that the serialization modules are functioning correctly.

In particular, these tests verify that the modifications made to the standard
Django serialization modules function correctly and that the combined datastore
and Django models can be dumped and loaded to all of the provided formats.
"""


import os
import re
import unittest
from StringIO import StringIO

from django.core import serializers

from google.appengine.ext import db
from appengine_django.models import BaseModel


class ModelA(BaseModel):
  description = db.StringProperty()


class ModelB(BaseModel):
  description = db.StringProperty()
  friend = db.Reference(ModelA)


class TestAllFormats(type):

  def __new__(cls, name, bases, attrs):
    """Extends base test functions to be called for every serialisation format.

    Looks for functions matching 'run.*Test', where the wildcard in the middle
    matches the desired test name and ensures that a test case is setup to call
    that function once for every defined serialisation format. The test case
    that is created will be called 'test<format><name>'. Eg, for the function
    'runKeyedObjectTest' functions like 'testJsonKeyedObject' will be created.
    """
    test_formats = serializers.get_serializer_formats()
    test_formats.remove("python")  # Python serializer is only used indirectly.

    for func_name in attrs.keys():
      m = re.match("^run(.*)Test$", func_name)
      if not m:
        continue
      for format in test_formats:
        test_name = "test%s%s" % (format.title(), m.group(1))
        test_func = eval("lambda self: getattr(self, \"%s\")(\"%s\")" %
                         (func_name, format))
        attrs[test_name] = test_func

    return super(TestAllFormats, cls).__new__(cls, name, bases, attrs)


class SerializationTest(unittest.TestCase):
  """Unit tests for the serialization/deserialization functionality.

  Tests that every loaded serialization format can successfully dump and then
  reload objects without the objects changing.
  """
  __metaclass__ = TestAllFormats

  def compareObjects(self, orig, new, format="unknown"):
    """Compares two objects to ensure they are identical.

    Args:
      orig: The original object, must be an instance of db.Model.
      new: The new object, must be an instance of db.Model.
      format: The serialization format being tested, used to make error output
        more helpful.

    Raises:
      The function has no return value, but will raise assertion errors if the
      objects do not match correctly.
    """
    if orig.key().name():
      # Only compare object keys when the key is named. Key IDs are not static
      # and will change between dump/load. If you want stable Keys they need to
      # be named!
      self.assertEqual(orig.key(), new.key(),
                       "keys not equal after %s serialization: %s != %s" %
                       (format, repr(orig.key()), repr(new.key())))

    for key in orig.properties().keys():
      oval = getattr(orig, key)
      nval = getattr(new, key)
      if isinstance(orig.properties()[key], db.Reference):
        # Need to compare object keys not the objects themselves.
        oval = oval.key()
        nval = nval.key()
      self.assertEqual(oval, nval, "%s attribute differs after %s "
                       "serialization: %s != %s" % (key, format, oval, nval))

  def doSerialisationTest(self, format, obj, rel_attr=None, obj_ref=None):
    """Runs a serialization test on an object for the specified format.

    Args:
      format: The name of the Django serialization class to use.
      obj: The object to {,de}serialize, must be an instance of db.Model.
      rel_attr: Name of the attribute of obj references another model.
      obj_ref: The expected object reference, must be an instance of db.Model.

    Raises:
      The function has no return value but raises assertion errors if the
      object cannot be successfully serialized and then deserialized back to an
      identical object. If rel_attr and obj_ref are specified the deserialized
      object must also retain the references from the original object.
    """
    serialised = serializers.serialize(format, [obj])
    # Try and get the object back from the serialized string.
    result = list(serializers.deserialize(format, StringIO(serialised)))
    self.assertEqual(1, len(result),
                     "%s serialization should create 1 object" % format)
    result[0].save()  # Must save back into the database to get a Key.
    self.compareObjects(obj, result[0].object, format)
    if rel_attr and obj_ref:
      rel = getattr(result[0].object, rel_attr)
      if callable(rel):
        rel = rel()
      self.compareObjects(rel, obj_ref, format)

  def doLookupDeserialisationReferenceTest(self, lookup_dict, format):
    """Tests the Key reference is loaded OK for a format.

    Args:
      lookup_dict: A dictionary indexed by format containing serialized strings
        of the objects to load.
      format: The format to extract from the dict and deserialize.

    Raises:
      This function has no return value but raises assertion errors if the
      string cannot be deserialized correctly or the resulting object does not
      reference the object correctly.
    """
    if format not in lookup_dict:
      # Check not valid for this format.
      return
    obj = ModelA(description="test object", key_name="test")
    obj.put()
    s = lookup_dict[format]
    result = list(serializers.deserialize(format, StringIO(s)))
    self.assertEqual(1, len(result), "expected 1 object from %s" % format)
    result[0].save()
    self.compareObjects(obj, result[0].object.friend, format)

  def doModelKeyDeserialisationReferenceTest(self, lookup_dict, format):
    """Tests a model with a key can be loaded OK for a format.

    Args:
      lookup_dict: A dictionary indexed by format containing serialized strings
        of the objects to load.
      format: The format to extract from the dict and deserialize.

    Returns:
      This function has no return value but raises assertion errors if the
      string cannot be deserialized correctly or the resulting object is not an
      instance of ModelA with a key named 'test'.
    """
    if format not in lookup_dict:
      # Check not valid for this format.
      return
    s = lookup_dict[format]
    result = list(serializers.deserialize(format, StringIO(s)))
    self.assertEqual(1, len(result), "expected 1 object from %s" % format)
    result[0].save()
    self.assert_(isinstance(result[0].object, ModelA))
    self.assertEqual("test", result[0].object.key().name())

  # Lookup dicts for the above (doLookupDeserialisationReferenceTest) function.
  SERIALIZED_WITH_KEY_AS_LIST = {
      "json": """[{"pk": "agR0ZXN0chMLEgZNb2RlbEIiB21vZGVsYmkM", """
              """"model": "tests.modelb", "fields": {"description": "test", """
              """"friend": ["ModelA", "test"] }}]""",
      "yaml": """- fields: {description: !!python/unicode 'test', friend: """
              """ [ModelA, test]}\n  model: tests.modelb\n  pk: """
              """ agR0ZXN0chMLEgZNb2RlbEEiB21vZGVsYWkM\n"""
  }
  SERIALIZED_WITH_KEY_REPR = {
      "json": """[{"pk": "agR0ZXN0chMLEgZNb2RlbEIiB21vZGVsYmkM", """
              """"model": "tests.modelb", "fields": {"description": "test", """
              """"friend": "datastore_types.Key.from_path("""
              """'ModelA', 'test')" }}]""",
      "yaml": """- fields: {description: !!python/unicode 'test', friend: """
              """\'datastore_types.Key.from_path("ModelA", "test")\'}\n  """
              """model: tests.modelb\n  pk: """
              """ agR0ZXN0chMLEgZNb2RlbEEiB21vZGVsYWkM\n"""
  }

  # Lookup dict for the doModelKeyDeserialisationReferenceTest function.
  MK_SERIALIZED_WITH_LIST = {
      "json": """[{"pk": ["ModelA", "test"], "model": "tests.modela", """
              """"fields": {}}]""",
      "yaml": """-\n fields: {description: null}\n model: tests.modela\n """
              """pk: [ModelA, test]\n"""
  }
  MK_SERIALIZED_WITH_KEY_REPR = {
      "json": """[{"pk": "datastore_types.Key.from_path('ModelA', 'test')", """
              """"model": "tests.modela", "fields": {}}]""",
      "yaml": """-\n fields: {description: null}\n model: tests.modela\n """
              """pk: \'datastore_types.Key.from_path("ModelA", "test")\'\n"""
  }
  MK_SERIALIZED_WITH_KEY_AS_TEXT = {
      "json": """[{"pk": "test", "model": "tests.modela", "fields": {}}]""",
      "yaml": """-\n fields: {description: null}\n model: tests.modela\n """
              """pk: test\n"""
  }

  # Lookup dict for the function.
  SERIALIZED_WITH_NON_EXISTANT_PARENT = {
      "json": """[{"pk": "ahhnb29nbGUtYXBwLWVuZ2luZS1kamFuZ29yIgsSBk1vZG"""
              """VsQiIGcGFyZW50DAsSBk1vZGVsQSIEdGVzdAw", """
              """"model": "tests.modela", "fields": """
              """{"description": null}}]""",
      "yaml": """- fields: {description: null}\n  """
              """model: tests.modela\n  """
              """pk: ahhnb29nbGUtYXBwLWVuZ2luZS1kamFuZ29yIgsSBk1"""
              """vZGVsQiIGcGFyZW50DAsSBk1vZGVsQSIEdGVzdAw\n""",
      "xml":  """<?xml version="1.0" encoding="utf-8"?>\n"""
              """<django-objects version="1.0">\n"""
              """<entity kind="tests.modela" key="ahhnb29nbGUtYXBwL"""
              """WVuZ2luZS1kamFuZ29yIgsSBk1vZGVsQiIGcGFyZW50DA"""
              """sSBk1vZGVsQSIEdGVzdAw">\n  """
              """<key>tag:google-app-engine-django.gmail.com,"""
              """2008-05-13:ModelA[ahhnb29nbGUtYXBwLWVuZ2luZS1kam"""
              """FuZ29yIgsSBk1vZGVsQiIGcGFyZW50DAsSBk1vZGVsQSIEdGVzdAw"""
              """]</key>\n  <property name="description" """
              """type="null"></property>\n</entity>\n</django-objects>"""
  }

  # The following functions are all expanded by the metaclass to be run once
  # for every registered Django serialization module.

  def runKeyedObjectTest(self, format):
    """Test serialization of a basic object with a named key."""
    obj = ModelA(description="test object", key_name="test")
    obj.put()
    self.doSerialisationTest(format, obj)

  def runObjectWithIdTest(self, format):
    """Test serialization of a basic object with a numeric ID key."""
    obj = ModelA(description="test object")
    obj.put()
    self.doSerialisationTest(format, obj)

  def runObjectWithReferenceTest(self, format):
    """Test serialization of an object that references another object."""
    obj = ModelA(description="test object", key_name="test")
    obj.put()
    obj2 = ModelB(description="friend object", friend=obj)
    obj2.put()
    self.doSerialisationTest(format, obj2, "friend", obj)

  def runObjectWithParentTest(self, format):
    """Test serialization of an object that has a parent object reference."""
    obj = ModelA(description="parent object", key_name="parent")
    obj.put()
    obj2 = ModelA(description="child object", key_name="child", parent=obj)
    obj2.put()
    self.doSerialisationTest(format, obj2, "parent", obj)

  def runObjectWithNonExistantParentTest(self, format):
    """Test deserialization of an object referencing a non-existant parent."""
    self.doModelKeyDeserialisationReferenceTest(
        self.SERIALIZED_WITH_NON_EXISTANT_PARENT, format)

  def runCreateKeyReferenceFromListTest(self, format):
    """Tests that a reference specified as a list in json/yaml can be loaded OK."""
    self.doLookupDeserialisationReferenceTest(self.SERIALIZED_WITH_KEY_AS_LIST,
                                              format)

  def runCreateKeyReferenceFromReprTest(self, format):
    """Tests that a reference specified as repr(Key) in can loaded OK."""
    self.doLookupDeserialisationReferenceTest(self.SERIALIZED_WITH_KEY_REPR,
                                              format)

  def runCreateModelKeyFromListTest(self, format):
    """Tests that a model key specified as a list can be loaded OK."""
    self.doModelKeyDeserialisationReferenceTest(self.MK_SERIALIZED_WITH_LIST,
                                                format)

  def runCreateModelKeyFromReprTest(self, format):
    """Tests that a model key specified as a repr(Key) can be loaded OK."""
    self.doModelKeyDeserialisationReferenceTest(
        self.MK_SERIALIZED_WITH_KEY_REPR, format)

  def runCreateModelKeyFromTextTest(self, format):
    """Tests that a reference specified as a plain key_name loads OK."""
    self.doModelKeyDeserialisationReferenceTest(
        self.MK_SERIALIZED_WITH_KEY_AS_TEXT, format)


if __name__ == '__main__':
  unittest.main()
