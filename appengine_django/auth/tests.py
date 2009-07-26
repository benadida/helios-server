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

BASIC_TESTS = """
>>> from google.appengine.api import users
>>> from models import User, AnonymousUser
>>> appengine_user = users.User("test@example.com")
>>> django_user = User.get_djangouser_for_user(appengine_user)
>>> django_user.email == appengine_user.email()
True
>>> django_user.username == appengine_user.nickname()
True
>>> django_user.user == appengine_user
True

>>> django_user.username = 'test2'
>>> key = django_user.save()
>>> django_user.username == 'test2'
True

>>> django_user2 = User.get_djangouser_for_user(appengine_user)
>>> django_user2 == django_user
True

>>> django_user.is_authenticated()
True
>>> django_user.is_staff
False
>>> django_user.is_active
True

>>> a = AnonymousUser()
>>> a.is_authenticated()
False
>>> a.is_staff
False
>>> a.is_active
False
>>> a.groups.all()
[]
>>> a.user_permissions.all()
[]


"""

__test__ = {'BASIC_TESTS': BASIC_TESTS}
