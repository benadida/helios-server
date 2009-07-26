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

"""Ensures the App Engine memcache API works as Django's memcache backend."""

import unittest

from django.core.cache import get_cache
from appengine_django import appid
from appengine_django import have_appserver


class AppengineMemcacheTest(unittest.TestCase):
  """Tests that the memcache backend works."""

  def setUp(self):
    """Get the memcache cache module so it is available to tests."""
    self._cache = get_cache("memcached://")

  def testSimpleSetGet(self):
    """Tests that a simple set/get operation through the cache works."""
    self._cache.set("test_key", "test_value")
    self.assertEqual(self._cache.get("test_key"), "test_value")

  def testDelete(self):
    """Tests that delete removes values from the cache."""
    self._cache.set("test_key", "test_value")
    self.assertEqual(self._cache.has_key("test_key"), True)
    self._cache.delete("test_key")
    self.assertEqual(self._cache.has_key("test_key"), False)
