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
import logging

from django.core.management.base import BaseCommand


def run_appcfg():
  # import this so that we run through the checks at the beginning
  # and report the appropriate errors
  import appcfg

  # We don't really want to use that one though, it just executes this one
  from google.appengine.tools import appcfg

  # Reset the logging level to WARN as appcfg will spew tons of logs on INFO
  logging.getLogger().setLevel(logging.WARN)

  # Note: if we decide to change the name of this command to something other
  #       than 'vacuum_indexes' we will have to munge the args to replace whatever
  #       we called it with 'vacuum_indexes'
  new_args = sys.argv[:]
  new_args.append('.')
  appcfg.main(new_args)


class Command(BaseCommand):
  """Calls the appcfg.py's vacuum_indexes command for the current project.

  Any additional arguments are passed directly to appcfg.py.
  """
  help = 'Calls appcfg.py vacuum_indexes for the current project.'
  args = '[any appcfg.py options]'

  def run_from_argv(self, argv):
    run_appcfg()
