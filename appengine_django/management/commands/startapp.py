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


import os

import django
from django.core.management.commands import startapp

import appengine_django


class Command(startapp.Command):
  def handle_label(self, *args, **kwds):
    """Temporary adjust django.__path__ to load app templates from the
    helpers directory.
    """
    old_path = django.__path__
    django.__path__ = appengine_django.__path__
    startapp.Command.handle_label(self, *args, **kwds)
    django.__path__ = old_path


class ProjectCommand(Command):
  def __init__(self, project_directory):
    super(ProjectCommand, self).__init__()
    self.project_directory = project_directory

  def handle_label(self, app_name, **options):
    super(ProjectCommand, self).handle_label(app_name, self.project_directory,
                                             **options)

