"""
server_ui specific views
"""

import copy

from django.conf import settings

import helios_auth.views as auth_views
from helios.models import Election
from helios.security import can_create_election
from helios_auth.security import get_user
from . import glue
from .view_utils import render_template

glue.glue()  # actually apply glue helios.view <-> helios.signals


def get_election():
  return None
  
def home(request):
  # load the featured elections
  featured_elections = Election.get_featured()
  
  user = get_user(request)
  create_p = can_create_election(request)

  if create_p:
    elections_administered = Election.get_by_user_as_admin(user, archived_p=False, limit=5)
  else:
    elections_administered = None

  if user:
    elections_voted = Election.get_by_user_as_voter(user, limit=5)
  else:
    elections_voted = None
 
  auth_systems = copy.copy(settings.AUTH_ENABLED_SYSTEMS)
  try:
    auth_systems.remove('password')
  except: pass

  login_box = auth_views.login_box_raw(request, return_url="/", auth_systems=auth_systems)

  return render_template(request, "index", {'elections': featured_elections,
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
    
