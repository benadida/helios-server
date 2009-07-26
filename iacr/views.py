"""
Votwee specific views
"""

from helios.models import *
from auth.security import *
from view_utils import *

import helios.views

from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpResponseNotAllowed

def home(request):
  user = get_user(request)
  if user:
    elections = Election.get_by_user_as_admin(user)
    elections_registered = Election.get_by_user_as_voter(user)
  else:
    elections = []
    elections_registered = []
    
  return render_template(request, "index", {'elections' : elections, 'elections_registered' : elections_registered})
  
def about(request):
  return HttpResponse(request, "about")
    
def election_shortcut(request, election_short_name):
  election = Election.get_by_short_name(election_short_name)
  return HttpResponseRedirect(reverse(helios.views.one_election_view, args=[election.uuid]))