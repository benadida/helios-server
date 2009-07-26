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


"""
Replaces the default Django XML serializer with one that uses the built in
ToXml method for each entity.
"""

import re

from django.conf import settings
from django.core.serializers import base
from django.core.serializers import xml_serializer
from django.db import models

from google.appengine.api import datastore_types
from google.appengine.ext import db

from python import FakeParent

getInnerText = xml_serializer.getInnerText


class Serializer(xml_serializer.Serializer):
  """A Django Serializer class to convert datastore models to XML.

  This class relies on the ToXml method of the entity behind each model to do
  the hard work.
  """

  def __init__(self, *args, **kwargs):
    super(Serializer, self).__init__(*args, **kwargs)
    self._objects = []

  def handle_field(self, obj, field):
    """Fields are not handled individually."""
    pass

  def handle_fk_field(self, obj, field):
    """Fields are not handled individually."""
    pass

  def start_object(self, obj):
    """Nothing needs to be done to start an object."""
    pass

  def end_object(self, obj):
    """Serialize the object to XML and add to the list of objects to output.

    The output of ToXml is manipulated to replace the datastore model name in
    the "kind" tag with the Django model name (which includes the Django
    application name) to make importing easier.
    """
    xml = obj._entity.ToXml()
    xml = xml.replace(u"""kind="%s" """ % obj._entity.kind(),
                      u"""kind="%s" """ % unicode(obj._meta))
    self._objects.append(xml)

  def getvalue(self):
    """Wrap the serialized objects with XML headers and return."""
    str = u"""<?xml version="1.0" encoding="utf-8"?>\n"""
    str += u"""<django-objects version="1.0">\n"""
    str += u"".join(self._objects)
    str += u"""</django-objects>"""
    return str


class Deserializer(xml_serializer.Deserializer):
  """A Django Deserializer class to convert XML to Django objects.

  This is a fairly manualy and simplistic XML parser, it supports just enough
  functionality to read the keys and fields for an entity from the XML file and
  construct a model object.
  """

  def next(self):
    """Replacement next method to look for 'entity'.

    The default next implementation exepects 'object' nodes which is not
    what the entity's ToXml output provides.
    """
    for event, node in self.event_stream:
      if event == "START_ELEMENT" and node.nodeName == "entity":
        self.event_stream.expandNode(node)
        return self._handle_object(node)
    raise StopIteration

  def _handle_object(self, node):
    """Convert an <entity> node to a DeserializedObject"""
    Model = self._get_model_from_node(node, "kind")
    data = {}
    key = db.Key(node.getAttribute("key"))
    if key.name():
      data["key_name"] = key.name()
    parent = None
    if key.parent():
      parent = FakeParent(key.parent())
    m2m_data = {}

    # Deseralize each field.
    for field_node in node.getElementsByTagName("property"):
      # If the field is missing the name attribute, bail (are you
      # sensing a pattern here?)
      field_name = field_node.getAttribute("name")
      if not field_name:
          raise base.DeserializationError("<field> node is missing the 'name' "
                                          "attribute")
      field = Model.properties()[field_name]
      field_value = getInnerText(field_node).strip()

      if isinstance(field, db.Reference):
        m = re.match("tag:.*\[(.*)\]", field_value)
        if not m:
          raise base.DeserializationError(u"Invalid reference value: '%s'" %
                                          field_value)
        key = m.group(1)
        key_obj = db.Key(key)
        if not key_obj.name():
          raise base.DeserializationError(u"Cannot load Reference with "
                                          "unnamed key: '%s'" % field_value)
        data[field.name] = key_obj
      else:
        data[field.name] = field.validate(field_value)

    # Create the new model instance with all it's data, but no parent.
    object = Model(**data)
    # Now add the parent into the hidden attribute, bypassing the type checks
    # in the Model's __init__ routine.
    object._parent = parent
    # When the deserialized object is saved our replacement DeserializedObject
    # class will set object._parent to force the real parent model to be loaded
    # the first time it is referenced.
    return base.DeserializedObject(object, m2m_data)
