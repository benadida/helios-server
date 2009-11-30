"""
server_ui specific views
"""

from helios.models import *
from auth.security import *
from view_utils import *

import helios.views
import helios
from helios.crypto import utils as cryptoutils
from auth.security import *

from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpResponseNotAllowed

from django.conf import settings


def get_election():
  return None
  
def home(request):
  # load the featured elections
  featured_elections = [Election.get_by_short_name(short_name) for short_name in settings.FEATURED_ELECTIONS]
  featured_elections = [e for e in featured_elections if e != None]
  
  return render_template(request, "index", {'elections': featured_elections})
  
def about(request):
  return HttpResponse(request, "about")
    
def cast(request):
  encrypted_vote = request.POST['encrypted_vote']
  request.session['encrypted_vote'] = encrypted_vote
  return HttpResponseRedirect(reverse(cast_confirm))

# the form for password login  
from auth.auth_systems.password import LoginForm, password_check

def cast_confirm(request):
  election = get_election()
  if not election.frozen_at or election.result:
    return HttpResponse("election is not ready or already done")

  # tallied election, no vote casting
  if election.encrypted_tally or election.result:
    return render_template(request, 'election_tallied', {'election': election})
  
  encrypted_vote = request.session['encrypted_vote']
  vote_fingerprint = cryptoutils.hash_b64(encrypted_vote)  
  
  error = None
  
  if request.method == "GET":
    form = LoginForm()
  else:
    form = LoginForm(request.POST)

    check_csrf(request)

    if form.is_valid():
      user = User.get_by_type_and_id('password', form.cleaned_data['username'])
      if password_check(user, form.cleaned_data['password']):
        # cast the actual vote
        voter = Voter.get_by_election_and_user(election, user)
        if not voter:
          return HttpResponse("problem, you are not registered for this election")
        
        # prepare the vote to cast
        cast_vote_params = {
          'vote' : electionalgs.EncryptedVote.fromJSONDict(utils.from_json(encrypted_vote)),
          'voter' : voter,
          'vote_hash': vote_fingerprint,
          'cast_at': datetime.datetime.utcnow(),
          'election': election
        }
    
        cast_vote = CastVote(**cast_vote_params)

        # verify the vote
        if cast_vote.vote.verify(election):
          # store it
          voter.store_vote(cast_vote)
        else:
          return HttpResponse("vote does not verify: " + utils.to_json(cast_vote.vote.toJSONDict()))

        # remove the vote from the store
        del request.session['encrypted_vote']
        
        return HttpResponseRedirect(reverse(cast_done) + '?email=' + voter.voter_id)
      else:
        error = 'Bad Username or Password'

  return render_template(request, "confirm", {'election': election, 'vote_fingerprint': vote_fingerprint, 'error': error, 'form': form})
  
def cast_done(request):
  email = request.GET['email']

  election = get_election()
  user = User.get_by_type_and_id('password', email)
  voter = Voter.get_by_election_and_user(election, user)
  past_votes = CastVote.get_by_election_and_voter(election, voter)
  
  return render_template(request, 'done', {'election': election, 'past_votes' : past_votes, 'voter': voter})
  