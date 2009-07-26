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

from django.contrib.auth.models import AnonymousUser

from google.appengine.api import users

from appengine_django.auth.models import User


class LazyUser(object):
  def __get__(self, request, obj_type=None):
    if not hasattr(request, '_cached_user'):
      user = users.get_current_user()
      if user:
        request._cached_user = User.get_djangouser_for_user(user)
      else:
        request._cached_user = AnonymousUser()
    return request._cached_user


class AuthenticationMiddleware(object):
  def process_request(self, request):
    request.__class__.user = LazyUser()
    return None
