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

"""This module looks after initialising the appengine api stubs."""

import logging
import os

from appengine_django import appid
from appengine_django import have_appserver
from appengine_django.db.creation import DatabaseCreation


from django.db.backends import BaseDatabaseWrapper
from django.db.backends import BaseDatabaseFeatures
from django.db.backends import BaseDatabaseOperations


def get_datastore_paths():
  """Returns a tuple with the path to the datastore and history file.

  The datastore is stored in the same location as dev_appserver uses by
  default, but the name is altered to be unique to this project so multiple
  Django projects can be developed on the same machine in parallel.

  Returns:
    (datastore_path, history_path)
  """
  from google.appengine.tools import dev_appserver_main
  datastore_path = dev_appserver_main.DEFAULT_ARGS['datastore_path']
  history_path = dev_appserver_main.DEFAULT_ARGS['history_path']
  datastore_path = datastore_path.replace("dev_appserver", "django_%s" % appid)
  history_path = history_path.replace("dev_appserver", "django_%s" % appid)
  return datastore_path, history_path


def get_test_datastore_paths(inmemory=True):
  """Returns a tuple with the path to the test datastore and history file.

  If inmemory is true, (None, None) is returned to request an in-memory
  datastore. If inmemory is false the path returned will be similar to the path
  returned by get_datastore_paths but with a different name.

  Returns:
    (datastore_path, history_path)
  """
  if inmemory:
    return None, None
  datastore_path, history_path = get_datastore_paths()
  datastore_path = datastore_path.replace("datastore", "testdatastore")
  history_path = history_path.replace("datastore", "testdatastore")
  return datastore_path, history_path


def destroy_datastore(datastore_path, history_path):
  """Destroys the appengine datastore at the specified paths."""
  for path in [datastore_path, history_path]:
    if not path: continue
    try:
      os.remove(path)
    except OSError, e:
      if e.errno != 2:
        logging.error("Failed to clear datastore: %s" % e)


class DatabaseError(Exception):
  """Stub class for database errors. Required by Django"""
  pass


class IntegrityError(Exception):
  """Stub class for database integrity errors. Required by Django"""
  pass


class DatabaseFeatures(BaseDatabaseFeatures):
  """Stub class to provide the feaures member expected by Django"""
  pass


class DatabaseOperations(BaseDatabaseOperations):
  """Stub class to provide the options member expected by Django"""
  pass


class DatabaseWrapper(BaseDatabaseWrapper):
  """App Engine database definition for Django.

  This "database" backend does not support any of the standard backend
  operations. The only task that it performs is to setup the api stubs required
  by the appengine libraries if they have not already been initialised by an
  appserver.
  """

  def __init__(self, *args, **kwargs):
    super(DatabaseWrapper, self).__init__(*args, **kwargs)
    self.features = DatabaseFeatures()
    self.ops = DatabaseOperations()
    self.creation = DatabaseCreation(self)
    self.use_test_datastore = kwargs.get("use_test_datastore", False)
    self.test_datastore_inmemory = kwargs.get("test_datastore_inmemory", True)
    if have_appserver:
      return
    self._setup_stubs()

  def _get_paths(self):
    if self.use_test_datastore:
      return get_test_datastore_paths(self.test_datastore_inmemory)
    else:
      return get_datastore_paths()

  def _setup_stubs(self):
    # If this code is being run without an appserver (eg. via a django
    # commandline flag) then setup a default stub environment.
    from google.appengine.tools import dev_appserver_main
    args = dev_appserver_main.DEFAULT_ARGS.copy()
    args['datastore_path'], args['history_path'] = self._get_paths()
    from google.appengine.tools import dev_appserver
    dev_appserver.SetupStubs(appid, **args)
    if self.use_test_datastore:
      logging.debug("Configured API stubs for the test datastore")
    else:
      logging.debug("Configured API stubs for the development datastore")

  def flush(self):
    """Helper function to remove the current datastore and re-open the stubs"""
    destroy_datastore(*self._get_paths())
    self._setup_stubs()

  def close(self):
    pass

  def _commit(self):
    pass

  def cursor(self, *args):
    pass
