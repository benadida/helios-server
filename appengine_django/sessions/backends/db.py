#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime

from django.contrib.sessions.backends import base
from django.core.exceptions import SuspiciousOperation

from appengine_django.sessions.models import Session


class SessionStore(base.SessionBase):
  """A key-based session store for Google App Engine."""

  def load(self):
    session = self._get_session(self.session_key)
    if session:
      try:
        return self.decode(session.session_data)
      except SuspiciousOperation:
        # Create a new session_key for extra security.
        pass
    self.session_key = self._get_new_session_key()
    self._session_cache = {}
    self.save()
    # Ensure the user is notified via a new cookie.
    self.modified = True
    return {}

  def save(self, must_create=False):
    if must_create and self.exists(self.session_key):
      raise base.CreateError
    session = Session(
        key_name='k:' + self.session_key,
        session_data = self.encode(self._session),
        expire_date = self.get_expiry_date())
    session.put()

  def exists(self, session_key):
    return Session.get_by_key_name('k:' + session_key) is not None

  def delete(self, session_key=None):
    if session_key is None:
      session_key = self._session_key
    session = self._get_session(session_key=session_key)
    if session:
      session.delete()

  def _get_session(self, session_key):
    session = Session.get_by_key_name('k:' + session_key)
    if session:
      if session.expire_date > datetime.now():
        return session
      session.delete()
    return None

  def create(self):
    while True:
      self.session_key = self._get_new_session_key()
      try:
        # Save immediately to ensure we have a unique entry in the
        # database.
        self.save(must_create=True)
      except base.CreateError:
        # Key wasn't unique. Try again.
        continue
      self.modified = True
      self._session_cache = {}
      return
