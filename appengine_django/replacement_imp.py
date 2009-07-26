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

"""This file acts as a very minimal replacement for the 'imp' module.

It contains only what Django expects to use and does not actually implement the
same functionality as the real 'imp' module.
"""


def find_module(name, path=None):
  """Django needs imp.find_module, but it works fine if nothing is found."""
  raise ImportError
