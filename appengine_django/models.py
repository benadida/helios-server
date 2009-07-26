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

import sys
import types

from google.appengine.ext import db

from django import VERSION
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.fields import Field
from django.db.models.options import Options
from django.db.models.loading import register_models, get_model


class ModelManager(object):
  """Replacement for the default Django model manager."""

  def __init__(self, owner):
    self.owner = owner

  def __getattr__(self, name):
    """Pass all attribute requests through to the real model"""
    return getattr(self.owner, name)


class ModelOptions(object):
  """Replacement for the default Django options class.

  This class sits at ._meta of each model. The primary information supplied by
  this class that needs to be stubbed out is the list of fields on the model.
  """

  def __init__(self, cls):
    self.object_name = cls.__name__
    self.module_name = self.object_name.lower()
    model_module = sys.modules[cls.__module__]
    self.app_label = model_module.__name__.split('.')[-2]
    self.abstract = False

  class pk:
    """Stub the primary key to always be 'key_name'"""
    name = "key_name"

  def __str__(self):
    return "%s.%s" % (self.app_label, self.module_name)

  @property
  def many_to_many(self):
    """The datastore does not support many to many relationships."""
    return []


class Relation(object):
  def __init__(self, to):
    self.field_name = "key_name"


def PropertyWrapper(prop):
  """Wrapper for db.Property to make it look like a Django model Property"""
  if isinstance(prop, db.Reference):
    prop.rel = Relation(prop.reference_class)
  else:
    prop.rel = None
  prop.serialize = True
  return prop


class PropertiedClassWithDjango(db.PropertiedClass):
  """Metaclass for the combined Django + App Engine model class.

  This metaclass inherits from db.PropertiedClass in the appengine library.
  This metaclass has two additional purposes:
  1) Register each model class created with Django (the parent class will take
     care of registering it with the appengine libraries).
  2) Add the (minimum number) of attributes and methods to make Django believe
     the class is a normal Django model.

  The resulting classes are still not generally useful as Django classes and
  are intended to be used by Django only in limited situations such as loading
  and dumping fixtures.
  """

  def __new__(cls, name, bases, attrs):
    """Creates a combined appengine and Django model.

    The resulting model will be known to both the appengine libraries and
    Django.
    """
    if name == 'BaseModel':
      # This metaclass only acts on subclasses of BaseModel.
      return super(PropertiedClassWithDjango, cls).__new__(cls, name,
                                                           bases, attrs)

    new_class = super(PropertiedClassWithDjango, cls).__new__(cls, name,
                                                              bases, attrs)

    new_class._meta = ModelOptions(new_class)
    new_class.objects = ModelManager(new_class)
    new_class._default_manager = new_class.objects
    new_class.DoesNotExist = types.ClassType('DoesNotExist',
                                             (ObjectDoesNotExist,), {})

    m = get_model(new_class._meta.app_label, name, False)
    if m:
      return m

    register_models(new_class._meta.app_label, new_class)
    return get_model(new_class._meta.app_label, name, False)

  def __init__(cls, name, bases, attrs):
    """Initialises the list of Django properties.

    This method takes care of wrapping the properties created by the superclass
    so that they look like Django properties and installing them into the
    ._meta object of the class so that Django can find them at the appropriate
    time.
    """
    super(PropertiedClassWithDjango, cls).__init__(name, bases, attrs)
    if name == 'BaseModel':
      # This metaclass only acts on subclasses of BaseModel.
      return

    fields = [PropertyWrapper(p) for p in cls._properties.values()]
    cls._meta.local_fields = fields


class BaseModel(db.Model):
  """Combined appengine and Django model.

  All models used in the application should derive from this class.
  """
  __metaclass__ = PropertiedClassWithDjango
 
  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return False
    return self._get_pk_val() == other._get_pk_val()

  def __ne__(self, other):
    return not self.__eq__(other)

  def _get_pk_val(self):
    """Return the string representation of the model's key"""
    return unicode(self.key())

  def __repr__(self):
    """Create a string that can be used to construct an equivalent object.

    e.g. eval(repr(obj)) == obj
    """
    # First, creates a dictionary of property names and values. Note that
    # property values, not property objects, has to be passed in to constructor.
    def _MakeReprTuple(prop_name):
      prop = getattr(self.__class__, prop_name)
      return (prop_name, prop.get_value_for_datastore(self))

    d = dict([_MakeReprTuple(prop_name) for prop_name in self.properties()])
    return "%s(**%s)" % (self.__class__.__name__, repr(d))


class RegistrationTestModel(BaseModel):
  """Used to check registration with Django is working correctly.

  Django 0.96 only recognises models defined within an applications models
  module when get_models() is called so this definition must be here rather
  than within the associated test (tests/model_test.py).
  """
  pass
