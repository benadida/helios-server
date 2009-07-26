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

"""Tests that the combined appengine and Django models function correctly."""


import unittest

from django import VERSION
from django.db.models import get_models
from django import forms

from google.appengine.ext.db import djangoforms
from google.appengine.ext import db

from appengine_django.models import BaseModel
from appengine_django.models import ModelManager
from appengine_django.models import ModelOptions
from appengine_django.models import RegistrationTestModel


class TestModelWithProperties(BaseModel):
  """Test model class for checking property -> Django field setup."""
  property1 = db.StringProperty()
  property2 = db.IntegerProperty()
  property3 = db.Reference()


class ModelTest(unittest.TestCase):
  """Unit tests for the combined model class."""

  def testModelRegisteredWithDjango(self):
    """Tests that a combined model class has been registered with Django."""
    self.assert_(RegistrationTestModel in get_models())

  def testDatastoreModelProperties(self):
    """Tests that a combined model class still has datastore properties."""
    self.assertEqual(3, len(TestModelWithProperties.properties()))

  def testDjangoModelClass(self):
    """Tests the parts of a model required by Django are correctly stubbed."""
    # Django requires model options to be found at ._meta.
    self.assert_(isinstance(RegistrationTestModel._meta, ModelOptions))
    # Django requires a manager at .objects
    self.assert_(isinstance(RegistrationTestModel.objects, ModelManager))
    # Django requires ._default_manager.
    self.assert_(hasattr(RegistrationTestModel, "_default_manager"))

  def testDjangoModelFields(self):
    """Tests that a combined model class has (faked) Django fields."""
    fields = TestModelWithProperties._meta.local_fields
    self.assertEqual(3, len(fields))
    # Check each fake field has the minimal properties that Django needs.
    for field in fields:
      # The Django serialization code looks for rel to determine if the field
      # is a relationship/reference to another model.
      self.assert_(hasattr(field, "rel"))
      # serialize is required to tell Django to serialize the field.
      self.assertEqual(True, field.serialize)
      if field.name == "property3":
        # Extra checks for the Reference field.
        # rel.field_name is used during serialization to find the field in the
        # other model that this field is related to. This should always be
        # 'key_name' for appengine models.
        self.assertEqual("key_name", field.rel.field_name)

  def testDjangoModelOptionsStub(self):
    """Tests that the options stub has the required properties by Django."""
    # Django requires object_name and app_label for serialization output.
    self.assertEqual("RegistrationTestModel",
                     RegistrationTestModel._meta.object_name)
    self.assertEqual("appengine_django", RegistrationTestModel._meta.app_label)
    # The pk.name member is required during serialization for dealing with
    # related fields.
    self.assertEqual("key_name", RegistrationTestModel._meta.pk.name)
    # The many_to_many method is called by Django in the serialization code to
    # find m2m relationships. m2m is not supported by the datastore.
    self.assertEqual([], RegistrationTestModel._meta.many_to_many)

  def testDjangoModelManagerStub(self):
    """Tests that the manager stub acts as Django would expect."""
    # The serialization code calls model.objects.all() to retrieve all objects
    # to serialize.
    self.assertEqual([], list(RegistrationTestModel.objects.all()))

  def testDjangoModelPK(self):
    """Tests that each model instance has a 'primary key' generated."""
    obj = RegistrationTestModel(key_name="test")
    obj.put()
    pk = obj._get_pk_val()
    self.assert_(pk)
    new_obj = RegistrationTestModel.get(pk)
    self.assertEqual(obj.key(), new_obj.key())

  def testModelFormPatched(self):
    """Tests that the Django ModelForm is being successfully patched."""
    self.assertEqual(djangoforms.ModelForm, forms.ModelForm)
