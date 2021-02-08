"""
Utilities for all views

Ben Adida (12-30-2008)
"""

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import loader
# nicely update the wrapper function
from functools import update_wrapper

import helios
from . import utils
from helios_auth.security import get_user

##
## BASICS
##

SUCCESS = HttpResponse("SUCCESS")

# FIXME: error code
FAILURE = HttpResponse("FAILURE")

##
## template abstraction
##
def prepare_vars(request, values):
  vars_with_user = values.copy() if values is not None else {}
  vars_with_user['user'] = get_user(request)

  # csrf protection
  if 'csrf_token' in request.session:
    vars_with_user['csrf_token'] = request.session['csrf_token']

  vars_with_user['utils'] = utils
  vars_with_user['settings'] = settings
  vars_with_user['HELIOS_STATIC'] = '/static/helios/helios'
  vars_with_user['TEMPLATE_BASE'] = helios.TEMPLATE_BASE
  vars_with_user['CURRENT_URL'] = request.path
  vars_with_user['SECURE_URL_HOST'] = settings.SECURE_URL_HOST

  return vars_with_user


def render_template(request, template_name, values = None, include_user=True):
  vars_with_user = prepare_vars(request, values)

  if not include_user:
    del vars_with_user['user']

  return render_to_response('helios/templates/%s.html' % template_name, vars_with_user)


def render_template_raw(request, template_name, values=None):
  t = loader.get_template(template_name)

  # if there's a request, prep the vars, otherwise can't do it.
  if request:
    full_vars = prepare_vars(request, values)
  else:
    full_vars = values or {}

  return t.render(context=full_vars, request=request)


def render_json(json_txt):
  return HttpResponse(utils.to_json(json_txt), content_type="application/json")


# decorator
def return_json(func):
    """
    A decorator that serializes the output to JSON before returning to the
    web client.
    """
    def convert_to_json(self, *args, **kwargs):
      return_val = func(self, *args, **kwargs)
      try:
        return render_json(return_val)
      except Exception as e:
        import logging
        logging.error("problem with serialization: " + str(return_val) + " / " + str(e))
        raise e

    return update_wrapper(convert_to_json,func)
