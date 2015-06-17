"""
server_ui specific views
"""

from helios.models import *
from helios_auth.security import *
from view_utils import *

import helios.views
import helios
from helios.crypto import utils as cryptoutils
from helios_auth.security import *
from helios.security import can_create_election

from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpResponseNotAllowed

from django.conf import settings

import copy
import helios_auth.views as auth_views

def get_election():
  return None
  
def home(request):
  # load the featured elections
  #featured_elections = helios.models.Election.get_featured()
  # 2015-06-10 include elections by "status"
  featured_elections_new = helios.models.Election.get_featured_new()
  featured_elections_in_progress = helios.models.Election.get_featured_in_progress()
  featured_elections_done = helios.models.Election.get_featured_done()
  
  user = get_user(request)
  create_p = can_create_election(request)

  if create_p:
    elections_administered = helios.models.Election.get_by_user_as_admin(user, archived_p=False, limit=5)
  else:
    elections_administered = None

  if user:
    elections_voted = helios.models.Election.get_by_user_as_voter(user, limit=5)
  else:
    elections_voted = None
 
  auth_systems = copy.copy(settings.AUTH_ENABLED_AUTH_SYSTEMS)
  try:
    auth_systems.remove('password')
  except: pass

  login_box = auth_views.login_box_raw(request, return_url="/", auth_systems=auth_systems)

  # include elections by "status"
  return render_template(request, "index", {'elections_new': featured_elections_new,
                                            'elections_in_progress': featured_elections_in_progress,
                                            'elections_done': featured_elections_done,
                                            'elections_administered' : elections_administered,
                                            'elections_voted' : elections_voted,
                                            'create_p':create_p,
                                            'login_box' : login_box})
  
def about(request):
  return render_template(request, "about")

def docs(request):
  return render_template(request, "docs")

def faq(request):
  return render_template(request, "faq")

def privacy(request):
  return render_template(request, "privacy")
    
