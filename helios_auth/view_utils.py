"""
Utilities for all views

Ben Adida (12-30-2008)
"""

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import loader

import helios_auth
from helios_auth.security import get_user

##
## BASICS
##

SUCCESS = HttpResponse("SUCCESS")

##
## template abstraction
##

def prepare_vars(request, values):
  vars_with_user = values.copy()

  if request:
    vars_with_user['user'] = get_user(request)
    vars_with_user['csrf_token'] = request.session['csrf_token']
    vars_with_user['SECURE_URL_HOST'] = settings.SECURE_URL_HOST

  vars_with_user['STATIC'] = '/static/auth'
  vars_with_user['MEDIA_URL'] = '/static/auth/'
  vars_with_user['TEMPLATE_BASE'] = helios_auth.TEMPLATE_BASE

  vars_with_user['settings'] = settings

  return vars_with_user


def render_template(request, template_name, values=None):
  vars_with_user = prepare_vars(request, values or {})

  return render_to_response('helios_auth/templates/%s.html' % template_name, vars_with_user)


def render_template_raw(request, template_name, values=None):
  t = loader.get_template(template_name + '.html')
  values = values or {}

  vars_with_user = prepare_vars(request, values)

  return t.render(context=vars_with_user, request=request)
