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


import logging

from django.conf import settings
from django.db.backends.creation import BaseDatabaseCreation


class DatabaseCreation(BaseDatabaseCreation):

  def create_test_db(self, *args, **kw):
    """Destroys the test datastore. A new store will be recreated on demand"""
    settings.DATABASE_SUPPORTS_TRANSACTIONS = False
    self.destroy_test_db()
    self.connection.use_test_datastore = True
    self.connection.flush()


  def destroy_test_db(self, *args, **kw):
    """Destroys the test datastore files."""
    from appengine_django.db.base import destroy_datastore
    from appengine_django.db.base import get_test_datastore_paths
    destroy_datastore(*get_test_datastore_paths())
    logging.debug("Destroyed test datastore")
