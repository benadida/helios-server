"""
IACR specific views
"""

from helios.models import *
from auth.security import *
from view_utils import *

import helios.views
import helios

from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpResponseNotAllowed

def home(request):
  # create the election if need be
  election_params = {
    'short_name' : 'iacr09',
    'name' : 'IACR 2009 Election',
    'description' : 'Election for the IACR Board - 2009',
    'uuid' : 'iacr',
    'cast_url' : reverse(cast),
    'self_registration' : False,
    'openreg': False,
    'admin' : helios.ADMIN
  }
  
  election = Election.get_by_key_name(election_params['short_name'])
  if not election:
    election = Election(key_name = election_params['short_name'], **election_params)
    election.put()
  
  return render_template(request, "index")
  
def about(request):
  return HttpResponse(request, "about")
    
@helios.views.election_view(frozen=True)
def cast(request, election):
  if request.method == "GET":
    encrypted_vote = request.POST['encrypted_vote']
    request.session['encrypted_vote'] = encrypted_vote
    return render_template(request, "cast", {'election': election})
  else:
    # do the casting
    pass
