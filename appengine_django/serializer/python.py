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
A Python "serializer", based on the default Django python serializer.

The only customisation is in the deserialization process which needs to take
special care to resolve the name and parent attributes of the key for each
entity and also recreate the keys for any references appropriately.
"""


from django.conf import settings
from django.core.serializers import base
from django.core.serializers import python
from django.db import models

from google.appengine.api import datastore_types
from google.appengine.ext import db

from django.utils.encoding import smart_unicode

Serializer = python.Serializer


class FakeParent(object):
  """Fake parent 'model' like object.

  This class exists to allow a parent object to be provided to a new model
  without having to load the parent instance itself.
  """

  def __init__(self, parent_key):
    self._entity = parent_key


def Deserializer(object_list, **options):
  """Deserialize simple Python objects back into Model instances.

  It's expected that you pass the Python objects themselves (instead of a
  stream or a string) to the constructor
  """
  models.get_apps()
  for d in object_list:
    # Look up the model and starting build a dict of data for it.
    Model = python._get_model(d["model"])
    data = {}
    key = resolve_key(Model._meta.module_name, d["pk"])
    if key.name():
      data["key_name"] = key.name()
    parent = None
    if key.parent():
      parent = FakeParent(key.parent())
    m2m_data = {}

    # Handle each field
    for (field_name, field_value) in d["fields"].iteritems():
      if isinstance(field_value, str):
        field_value = smart_unicode(
            field_value, options.get("encoding",
                                     settings.DEFAULT_CHARSET),
            strings_only=True)
      field = Model.properties()[field_name]

      if isinstance(field, db.Reference):
        # Resolve foreign key references.
        data[field.name] = resolve_key(Model._meta.module_name, field_value)
        if not data[field.name].name():
          raise base.DeserializationError(u"Cannot load Reference with "
                                          "unnamed key: '%s'" % field_value)
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
    yield base.DeserializedObject(object, m2m_data)


def resolve_key(model, key_data):
  """Creates a Key instance from a some data.

  Args:
    model: The name of the model this key is being resolved for. Only used in
      the fourth case below (a plain key_name string).
    key_data: The data to create a key instance from. May be in four formats:
      * The str() output of a key instance. Eg. A base64 encoded string.
      * The repr() output of a key instance. Eg. A string for eval().
      * A list of arguments to pass to db.Key.from_path.
      * A single string value, being the key_name of the instance. When this
        format is used the resulting key has no parent, and is for the model
        named in the model parameter.

  Returns:
    An instance of db.Key. If the data cannot be used to create a Key instance
    an error will be raised.
  """
  if isinstance(key_data, list):
    # The key_data is a from_path sequence.
    return db.Key.from_path(*key_data)
  elif isinstance(key_data, basestring):
    if key_data.find("from_path") != -1:
      # key_data is encoded in repr(key) format
      return eval(key_data)
    else:
      try:
        # key_data encoded a str(key) format
        return db.Key(key_data)
      except datastore_types.datastore_errors.BadKeyError, e:
        # Final try, assume it's a plain key name for the model.
        return db.Key.from_path(model, key_data)
  else:
    raise base.DeserializationError(u"Invalid key data: '%s'" % key_data)
