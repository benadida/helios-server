"""
Utilities for single election views

Ben Adida (2009-07-18)
"""

from django.template import Context, Template, loader
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response

from helios_auth.security import get_user

from django.conf import settings

##
## template abstraction
##
def render_template(request, template_name, vars = {}):
  t = loader.get_template(template_name + '.html')
  
  vars_with_user = vars.copy()
  vars_with_user['user'] = get_user(request)
  vars_with_user['settings'] = settings
  vars_with_user['CURRENT_URL'] = request.path
  
  # csrf protection
  if request.session.has_key('csrf_token'):
    vars_with_user['csrf_token'] = request.session['csrf_token']
  
  return render_to_response('heliosinstitution/templates/%s.html' % template_name, vars_with_user)
  
