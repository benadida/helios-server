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
import code
import getpass
import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand

from google.appengine.ext.remote_api import remote_api_stub


def auth_func():
  return raw_input('Username:'), getpass.getpass('Password:')

class Command(BaseCommand):
  """ Start up an interactive console backed by your app using remote_api """
  
  help = 'Start up an interactive console backed by your app using remote_api.'

  def run_from_argv(self, argv):
    app_id = argv[2]
    if len(argv) > 3:
      host = argv[3]
    else:
      host = '%s.appspot.com' % app_id

    remote_api_stub.ConfigureRemoteDatastore(app_id, 
                                             '/remote_api',
                                             auth_func,
                                             host)
      
    code.interact('App Engine interactive console for %s' % (app_id,), 
                  None,
                  locals())
