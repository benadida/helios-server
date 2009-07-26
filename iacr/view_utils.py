"""
Utilities for iacr views

Ben Adida (2009-07-18)
"""

from django.template import Context, Template, loader
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response

from auth.security import get_user

##
## template abstraction
##
def render_template(request, template_name, vars = {}):
  t = loader.get_template(template_name + '.html')
  
  vars_with_user = vars.copy()
  vars_with_user['user'] = get_user(request)
  
  return render_to_response('iacr/templates/%s.html' % template_name, vars_with_user)
  
