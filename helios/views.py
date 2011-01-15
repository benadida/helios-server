# -*- coding: utf-8 -*-
"""
Helios Django Views

Ben Adida (ben@adida.net)
"""

from django.core.urlresolvers import reverse
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.http import *
from django.db import transaction

from mimetypes import guess_type

import csv, urllib

from crypto import algs, electionalgs
from crypto import utils as cryptoutils
from helios import utils as helios_utils
from view_utils import *
from auth.security import *
from helios import security
from auth import views as auth_views

import tasks

from security import *
from auth.security import get_user, save_in_session_across_logouts

import uuid, datetime

from models import *

import forms, signals

# Parameters for everything
ELGAMAL_PARAMS = algs.ElGamal()
#ELGAMAL_PARAMS.p = 169989719781940995935039590956086833929670733351333885026079217526937746166790934510618940073906514429409914370072173967782198129423558224854191320917329420870526887804017711055077916007496804049206725568956610515399196848621653907978580213217522397058071043503404700268425750722626265208099856407306527012763L
#ELGAMAL_PARAMS.q = 84994859890970497967519795478043416964835366675666942513039608763468873083395467255309470036953257214704957185036086983891099064711779112427095660458664710435263443902008855527538958003748402024603362784478305257699598424310826953989290106608761198529035521751702350134212875361313132604049928203653263506381L
#ELGAMAL_PARAMS.g = 68111451286792593845145063691659993410221812806874234365854504719057401858372594942893291581957322023471947260828209362467690671421429979048643907159864269436501403220400197614308904460547529574693875218662505553938682573554719632491024304637643868603338114042760529545510633271426088675581644231528918421974L

# trying new ones from OlivierP
ELGAMAL_PARAMS.p = 16328632084933010002384055033805457329601614771185955389739167309086214800406465799038583634953752941675645562182498120750264980492381375579367675648771293800310370964745767014243638518442553823973482995267304044326777047662957480269391322789378384619428596446446984694306187644767462460965622580087564339212631775817895958409016676398975671266179637898557687317076177218843233150695157881061257053019133078545928983562221396313169622475509818442661047018436264806901023966236718367204710755935899013750306107738002364137917426595737403871114187750804346564731250609196846638183903982387884578266136503697493474682071L
ELGAMAL_PARAMS.q = 61329566248342901292543872769978950870633559608669337131139375508370458778917L
ELGAMAL_PARAMS.g = 14887492224963187634282421537186040801304008017743492304481737382571933937568724473847106029915040150784031882206090286938661464458896494215273989547889201144857352611058572236578734319505128042602372864570426550855201448111746579871811249114781674309062693442442368697449970648232621880001709535143047913661432883287150003429802392229361583608686643243349727791976247247948618930423866180410558458272606627111270040091203073580238905303994472202930783207472394578498507764703191288249547659899997131166130259700604433891232298182348403175947450284433411265966789131024573629546048637848902243503970966798589660808533L


# single election server? Load the single electionfrom models import Election
from django.conf import settings

# a helper function
def get_election_url(election):
  return settings.URL_HOST + reverse(election_shortcut, args=[election.short_name])  

# simple static views
def home(request):
  user = get_user(request)
  if user:
    elections = Election.get_by_user_as_admin(user, archived_p = False)
  else:
    elections = []
  
  return render_template(request, "index", {'elections' : elections})
  
def stats(request):
  user = get_user(request)
  if not user or not user.admin_p:
    raise PermissionDenied()

  page = int(request.GET.get('page', 1))
  limit = int(request.GET.get('limit', 25))

  elections = Election.objects.all().order_by('-created_at')
  elections_paginator = Paginator(elections, limit)
  elections_page = elections_paginator.page(page)

  return render_template(request, "stats", {'elections' : elections_page.object_list, 'elections_page': elections_page,
                                            'limit' : limit})


def get_voter(request, user, election):
  """
  return the current voter
  """
  voter = None
  if request.session.has_key('CURRENT_VOTER'):
    voter = request.session['CURRENT_VOTER']
    if voter.election != election:
      voter = None

  if not voter:
    if user:
      voter = Voter.get_by_election_and_user(election, user)
  
  return voter

##
## General election features
##

@json
def election_params(request):
  return ELGAMAL_PARAMS.toJSONDict()

def election_verifier(request):
  return render_template(request, "tally_verifier")

def election_single_ballot_verifier(request):
  return render_template(request, "ballot_verifier")

def election_shortcut(request, election_short_name):
  election = Election.get_by_short_name(election_short_name)
  if election:
    return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))
  else:
    raise Http404

def castvote_shortcut(request, vote_tinyhash):
  try:
    cast_vote = CastVote.objects.get(vote_tinyhash = vote_tinyhash)
  except CastVote.DoesNotExist:
    raise Http404

  # FIXME: consider privacy of election
  return render_template(request, 'castvote', {'cast_vote' : cast_vote, 'voter': cast_vote.voter, 'election': cast_vote.voter.election})

@trustee_check
def trustee_keygenerator(request, election, trustee):
  """
  A key generator with the current params, like the trustee home but without a specific election.
  """
  eg_params_json = utils.to_json(ELGAMAL_PARAMS.toJSONDict())

  return render_template(request, "election_keygenerator", {'eg_params_json': eg_params_json, 'election': election, 'trustee': trustee})

@login_required
def elections_administered(request):
  if not can_create_election(request):
    return HttpResponseForbidden('only an administrator has elections to administer')
  
  user = get_user(request)
  elections = Election.get_by_user_as_admin(user)
  
  return render_template(request, "elections_administered", {'elections': elections})
    

@login_required
def election_new(request):
  if not can_create_election(request):
    return HttpResponseForbidden('only an administrator can create an election')
    
  error = None
  
  if request.method == "GET":
    election_form = forms.ElectionForm()
  else:
    election_form = forms.ElectionForm(request.POST)
    
    if election_form.is_valid():
      # create the election obj
      election_params = dict(election_form.cleaned_data)
      
      # is the short name valid
      if helios_utils.urlencode(election_params['short_name']) == election_params['short_name']:      
        election_params['uuid'] = str(uuid.uuid1())
        election_params['cast_url'] = settings.SECURE_URL_HOST + reverse(one_election_cast, args=[election_params['uuid']])
      
        # registration starts closed
        election_params['openreg'] = False

        user = get_user(request)
        election_params['admin'] = user
        
        election, created_p = Election.get_or_create(**election_params)
      
        if created_p:
          return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))
        else:
          error = "An election with short name %s already exists" % election_params['short_name']
      else:
        error = "No special characters allowed in the short name."
    
  return render_template(request, "election_new", {'election_form': election_form, 'error': error})
  
@election_admin(frozen=False)
def one_election_edit(request, election):

  error = None
  RELEVANT_FIELDS = ['short_name', 'name', 'description', 'use_voter_aliases', 'election_type', 'advanced_audit_features', 'private_p']
  
  if request.method == "GET":
    values = {}
    for attr_name in RELEVANT_FIELDS:
      values[attr_name] = getattr(election, attr_name)
    election_form = forms.ElectionForm(values)
  else:
    election_form = forms.ElectionForm(request.POST)
    
    if election_form.is_valid():
      clean_data = election_form.cleaned_data
      for attr_name in RELEVANT_FIELDS:
        setattr(election, attr_name, clean_data[attr_name])

      election.save()
        
      return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))
  
  return render_template(request, "election_edit", {'election_form' : election_form, 'election' : election, 'error': error})

@election_admin(frozen=False)
def one_election_schedule(request, election):
  return HttpResponse("foo")

@election_view()
@json
def one_election(request, election):
  if not election:
    raise Http404
  return election.toJSONDict()

@election_view()
def election_badge(request, election):
  election_url = get_election_url(election)
  params = {'election': election, 'election_url': election_url}
  for option_name in ['show_title', 'show_vote_link']:
    params[option_name] = (request.GET.get(option_name, '1') == '1')
  return render_template(request, "election_badge", params)

@election_view()
def one_election_view(request, election):
  user = get_user(request)
  admin_p = security.user_can_admin_election(user, election)
  can_feature_p = security.user_can_feature_election(user, election)
  
  notregistered = False
  eligible_p = True
  
  election_url = get_election_url(election)
  status_update_message = None

  vote_url = "%s/booth/vote.html?%s" % (settings.SECURE_URL_HOST, urllib.urlencode({'election_url' : reverse(one_election, args=[election.uuid])}))

  test_cookie_url = "%s?%s" % (reverse(test_cookie), urllib.urlencode({'continue_url' : vote_url}))
  
  if user:
    voter = Voter.get_by_election_and_user(election, user)
    
    if voter:
      # cast any votes?
      votes = CastVote.get_by_voter(voter)
    else:
      eligible_p = _check_eligibility(election, user)
      votes = None
      notregistered = True
  else:
    voter = None
    votes = None

  # status update message?
  if election.openreg:
    if election.voting_has_started:
      status_update_message = u"Vote in %s" % election.name
    else:
      status_update_message = u"Register to vote in %s" % election.name

  # result!
  if election.result:
    status_update_message = u"Results are in for %s" % election.name
  
  # a URL for the social buttons
  socialbuttons_url = None
  if status_update_message:
    socialbuttons_url = "%s%s?%s" % (settings.SOCIALBUTTONS_URL_HOST,
                                     reverse(socialbuttons),
                                     urllib.urlencode({
          'url' : election_url,
          'text': status_update_message.encode('utf-8')
          }))

  trustees = Trustee.get_by_election(election)
    
  return render_template(request, 'election_view',
                         {'election' : election, 'trustees': trustees, 'admin_p': admin_p, 'user': user,
                          'voter': voter, 'votes': votes, 'notregistered': notregistered, 'eligible_p': eligible_p,
                          'can_feature_p': can_feature_p, 'election_url' : election_url, 'vote_url': vote_url,
                          'test_cookie_url': test_cookie_url, 'socialbuttons_url' : socialbuttons_url})

def test_cookie(request):
  continue_url = request.GET['continue_url']
  request.session.set_test_cookie()
  next_url = "%s?%s" % (reverse(test_cookie_2), urllib.urlencode({'continue_url': continue_url}))
  return HttpResponseRedirect(next_url)  

def test_cookie_2(request):
  continue_url = request.GET['continue_url']

  if not request.session.test_cookie_worked():
    return HttpResponseRedirect("%s?%s" % (reverse(nocookies), urllib.urlencode({'continue_url': continue_url})))

  request.session.delete_test_cookie()
  return HttpResponseRedirect(continue_url)  

def nocookies(request):
  retest_url = "%s?%s" % (reverse(test_cookie), urllib.urlencode({'continue_url' : request.GET['continue_url']}))
  return render_template(request, 'nocookies', {'retest_url': retest_url})

def socialbuttons(request):
  """
  just render the social buttons for sharing a URL
  expecting "url" and "text" in request.GET
  """
  return render_template(request, 'socialbuttons',
                         {'url': request.GET['url'], 'text':request.GET['text']})

##
## Trustees and Public Key
##
## As of July 2009, there are always trustees for a Helios election: one trustee is acceptable, for simple elections.
##
@json
@election_view()
def list_trustees(request, election):
  trustees = Trustee.get_by_election(election)
  return [t.toJSONDict() for t in trustees]
  
@election_view()
def list_trustees_view(request, election):
  trustees = Trustee.get_by_election(election)
  user = get_user(request)
  admin_p = security.user_can_admin_election(user, election)
  
  return render_template(request, 'list_trustees', {'election': election, 'trustees': trustees, 'admin_p':admin_p})
  
@election_admin(frozen=False)
def new_trustee(request, election):
  if request.method == "GET":
    return render_template(request, 'new_trustee', {'election' : election})
  else:
    # get the public key and the hash, and add it
    name = request.POST['name']
    email = request.POST['email']
    
    trustee = Trustee(uuid = str(uuid.uuid1()), election = election, name=name, email=email)
    trustee.save()
    return HttpResponseRedirect(reverse(list_trustees_view, args=[election.uuid]))

@election_admin(frozen=False)
def new_trustee_helios(request, election):
  """
  Make Helios a trustee of the election
  """
  election.generate_trustee(ELGAMAL_PARAMS)
  return HttpResponseRedirect(reverse(list_trustees_view, args=[election.uuid]))
  
@election_admin(frozen=False)
def delete_trustee(request, election):
  trustee = Trustee.get_by_election_and_uuid(election, request.GET['uuid'])
  trustee.delete()
  return HttpResponseRedirect(reverse(list_trustees_view, args=[election.uuid]))
  
def trustee_login(request, election_short_name, trustee_email, trustee_secret):
  election = Election.get_by_short_name(election_short_name)
  if election:
    trustee = Trustee.get_by_election_and_email(election, trustee_email)
    
    if trustee and trustee.secret == trustee_secret:
      set_logged_in_trustee(request, trustee)
      return HttpResponseRedirect(reverse(trustee_home, args=[election.uuid, trustee.uuid]))

  return HttpResponseRedirect("/")

@election_admin()
def trustee_send_url(request, election, trustee_uuid):
  trustee = Trustee.get_by_election_and_uuid(election, trustee_uuid)
  
  url = settings.SECURE_URL_HOST + reverse(trustee_login, args=[election.short_name, trustee.email, trustee.secret])
  
  body = """

You are a trustee for %s.

Your trustee dashboard is at

  %s
  
--
Helios  
""" % (election.name, url)

  send_mail('your trustee homepage for %s' % election.name, body, settings.SERVER_EMAIL, ["%s <%s>" % (trustee.name, trustee.email)], fail_silently=True)

  logging.info("URL %s " % url)
  return HttpResponseRedirect(reverse(list_trustees_view, args = [election.uuid]))

@trustee_check
def trustee_home(request, election, trustee):
  return render_template(request, 'trustee_home', {'election': election, 'trustee':trustee})
  
@trustee_check
def trustee_check_sk(request, election, trustee):
  return render_template(request, 'trustee_check_sk', {'election': election, 'trustee':trustee})
  
@trustee_check
def trustee_upload_pk(request, election, trustee):
  if request.method == "POST":
    # get the public key and the hash, and add it
    public_key_and_proof = utils.from_json(request.POST['public_key_json'])
    trustee.public_key = algs.EGPublicKey.fromJSONDict(public_key_and_proof['public_key'])
    trustee.pok = algs.DLogProof.fromJSONDict(public_key_and_proof['pok'])
    
    # verify the pok
    if not trustee.public_key.verify_sk_proof(trustee.pok, algs.DLog_challenge_generator):
      raise Exception("bad pok for this public key")
    
    trustee.public_key_hash = utils.hash_b64(utils.to_json(trustee.public_key.toJSONDict()))

    trustee.save()
    
    # send a note to admin
    try:
      election.admin.send_message("%s - trustee pk upload" % election.name, "trustee %s (%s) uploaded a pk." % (trustee.name, trustee.email))
    except:
      # oh well, no message sent
      pass
    
  return HttpResponseRedirect(reverse(trustee_home, args=[election.uuid, trustee.uuid]))

##
## Ballot Management
##

@json
@election_view(frozen=True)
def encrypt_ballot(request, election):
  """
  perform the ballot encryption given answers_json, a JSON'ified list of list of answers
  (list of list because each question could have a list of answers if more than one.)
  """
  # FIXME: maybe make this just request.POST at some point?
  answers = utils.from_json(request.REQUEST['answers_json'])
  ev = electionalgs.EncryptedVote.fromElectionAndAnswers(election, answers)
  return ev.toJSONDict(with_randomness=True)
    
@election_view(frozen=True)
def post_audited_ballot(request, election):
  if request.method == "POST":
    raw_vote = request.POST['audited_ballot']
    encrypted_vote = electionalgs.EncryptedVote.fromJSONDict(utils.from_json(raw_vote))
    vote_hash = encrypted_vote.get_hash()
    audited_ballot = AuditedBallot(raw_vote = raw_vote, vote_hash = vote_hash, election = election)
    audited_ballot.save()
    
    return SUCCESS
    

@election_view(frozen=True)
def one_election_cast(request, election):
  """
  on a GET, this is a cancellation, on a POST it's a cast
  """
  if request.method == "GET":
    return HttpResponseRedirect("%s%s" % (settings.URL_HOST, reverse(one_election_view, args = [election.uuid])))
    
  user = get_user(request)    
  encrypted_vote = request.POST['encrypted_vote']

  save_in_session_across_logouts(request, 'encrypted_vote', encrypted_vote)

  return HttpResponseRedirect("%s%s" % (settings.SECURE_URL_HOST, reverse(one_election_cast_confirm, args=[election.uuid])))

@election_view(frozen=True)
def password_voter_login(request, election):
  """
  This is used to log in as a voter for a particular election
  """
  password_login_form = forms.VoterPasswordForm(request.POST)
  if password_login_form.is_valid():
    try:
      voter = election.voter_set.get(voter_login_id = password_login_form.cleaned_data['voter_id'],
                                     voter_password = password_login_form.cleaned_data['password'])

      request.session['CURRENT_VOTER'] = voter
    except Voter.DoesNotExist:
      pass
  
  return HttpResponseRedirect(reverse(one_election_cast_confirm, args = [election.uuid]))

@election_view(frozen=True)
def one_election_cast_confirm(request, election):
  user = get_user(request)    

  # if no encrypted vote, the user is reloading this page or otherwise getting here in a bad way
  if not request.session.has_key('encrypted_vote'):
    return HttpResponseRedirect(settings.URL_HOST)

  voter = get_voter(request, user, election)

  # auto-register this person if the election is openreg
  if user and not voter and election.openreg:
    voter = _register_voter(election, user)
    
  # tallied election, no vote casting
  if election.encrypted_tally or election.result:
    return render_template(request, 'election_tallied', {'election': election})
    
  encrypted_vote = request.session['encrypted_vote']
  vote_fingerprint = cryptoutils.hash_b64(encrypted_vote)

  # if this user is a voter, prepare some stuff
  if voter:
    # prepare the vote to cast
    cast_vote_params = {
      'vote' : electionalgs.EncryptedVote.fromJSONDict(utils.from_json(encrypted_vote)),
      'voter' : voter,
      'vote_hash': vote_fingerprint,
      'cast_at': datetime.datetime.utcnow()
    }

    cast_vote = CastVote(**cast_vote_params)
  else:
    cast_vote = None
    
  if request.method == "GET":
    if voter:
      past_votes = CastVote.get_by_voter(voter)
      if len(past_votes) == 0:
        past_votes = None
    else:
      past_votes = None

    if cast_vote:
      # check for issues
      issues = cast_vote.issues(election)
    else:
      issues = None

    # status update this vote
    if voter and user and user.can_update_status():
      status_update_label = voter.user.update_status_template() % "your smart ballot tracker"
      status_update_message = "I voted in %s - my smart tracker is %s.. #heliosvoting" % (get_election_url(election),cast_vote.vote_hash[:10])
    else:
      status_update_label = None
      status_update_message = None

    # do we need to constrain the auth_systems?
    if election.eligibility:
      auth_systems = [e['auth_system'] for e in election.eligibility]
    else:
      auth_systems = None

    if auth_systems == ['password']:
      password_only = True
      password_login_form = forms.VoterPasswordForm()
    else:
      password_only = False
      password_login_form = None

    return_url = reverse(one_election_cast_confirm, args=[election.uuid])
    login_box = auth_views.login_box_raw(request, return_url=return_url, auth_systems = auth_systems)

    return render_template(request, 'election_cast_confirm', {
        'login_box': login_box, 'election' : election, 'vote_fingerprint': vote_fingerprint,
        'past_votes': past_votes, 'issues': issues, 'voter' : voter,
        'status_update_label': status_update_label, 'status_update_message': status_update_message,
        'password_only': password_only, 'password_login_form': password_login_form})
      
  if request.method == "POST":
    check_csrf(request)
    
    # voting has not started or has ended
    if (not election.voting_has_started()) or election.voting_has_stopped():
      return HttpResponseRedirect(settings.URL_HOST)
            
    # if user is not logged in
    # bring back to the confirmation page to let him know
    if not user or not voter:
      return HttpResponseRedirect(reverse(one_election_cast_confirm, args=[election.uuid]))
    
    # don't store the vote in the voter's data structure until verification
    cast_vote.save()

    # status update?
    if request.POST.get('status_update', False):
      status_update_message = request.POST.get('status_update_message')
    else:
      status_update_message = None

    # launch the verification task
    tasks.cast_vote_verify_and_store.delay(
      cast_vote_id = cast_vote.id,
      status_update_message = status_update_message)
    
    # remove the vote from the store
    del request.session['encrypted_vote']
    
    return HttpResponseRedirect("%s%s" % (settings.URL_HOST, reverse(one_election_cast_done, args=[election.uuid])))
  
@election_view()
def one_election_cast_done(request, election):
  """
  This view needs to be loaded because of the IFRAME, but then this causes 
  problems if someone clicks "reload". So we need a strategy.
  We store the ballot hash in the session
  """
  user = get_user(request)
  voter = get_voter(request, user, election)

  if voter:
    votes = CastVote.get_by_voter(voter)
    vote_hash = votes[0].vote_hash

    logout = settings.LOGOUT_ON_CONFIRMATION

    save_in_session_across_logouts(request, 'last_vote_hash', vote_hash)
  else:
    vote_hash = request.session['last_vote_hash']
    logout = False
  
  # local logout ensures that there's no more
  # user locally
  # WHY DO WE COMMENT THIS OUT? because we want to force a full logout via the iframe, including
  # from remote systems, just in case, i.e. CAS
  # if logout:
  #   auth_views.do_local_logout(request)
    
  # remote logout is happening asynchronously in an iframe to be modular given the logout mechanism
  return render_template(request, 'cast_done', {'election': election, 'vote_hash': vote_hash, 'logout': logout}, include_user=False)

@election_view()
@json
def one_election_result(request, election):
  return election.result

@election_view()
@json
def one_election_result_proof(request, election):
  return election.result_proof
  
@election_view(frozen=True)
def one_election_bboard(request, election):
  """
  UI to show election bboard
  """
  after = request.GET.get('after', None)
  offset= int(request.GET.get('offset', 0))
  limit = int(request.GET.get('limit', 50))
  
  order_by = 'voter_id'
  
  # unless it's by alias, in which case we better go by UUID
  if election.use_voter_aliases:
    order_by = 'alias'

  # if there's a specific voter
  if request.GET.has_key('q'):
    # FIXME: figure out the voter by voter_id
    voters = []
  else:
    # load a bunch of voters
    voters = Voter.get_by_election(election, after=after, limit=limit+1, order_by=order_by)
    
  more_p = len(voters) > limit
  if more_p:
    voters = voters[0:limit]
    next_after = getattr(voters[limit-1], order_by)
  else:
    next_after = None
    
  return render_template(request, 'election_bboard', {'election': election, 'voters': voters, 'next_after': next_after,
                'offset': offset, 'limit': limit, 'offset_plus_one': offset+1, 'offset_plus_limit': offset+limit,
                'voter_id': request.GET.get('voter_id', '')})

@election_view(frozen=True)
def one_election_audited_ballots(request, election):
  """
  UI to show election audited ballots
  """
  
  if request.GET.has_key('vote_hash'):
    b = AuditedBallot.get(election, request.GET['vote_hash'])
    return HttpResponse(b.raw_vote, mimetype="text/plain")
    
  after = request.GET.get('after', None)
  offset= int(request.GET.get('offset', 0))
  limit = int(request.GET.get('limit', 50))
  
  audited_ballots = AuditedBallot.get_by_election(election, after=after, limit=limit+1)
    
  more_p = len(audited_ballots) > limit
  if more_p:
    audited_ballots = audited_ballots[0:limit]
    next_after = audited_ballots[limit-1].vote_hash
  else:
    next_after = None
    
  return render_template(request, 'election_audited_ballots', {'election': election, 'audited_ballots': audited_ballots, 'next_after': next_after,
                'offset': offset, 'limit': limit, 'offset_plus_one': offset+1, 'offset_plus_limit': offset+limit})

@election_admin()
def voter_delete(request, election, voter_uuid):
  """
  Two conditions under which a voter can be deleted:
  - election is not frozen or
  - election is open reg
  """
  # if election is frozen and has closed registration
  if election.frozen_at and (not election.openreg):
    raise PermissionDenied()

  if election.encrypted_tally:
    raise PermissionDenied()

  voter = Voter.get_by_election_and_uuid(election, voter_uuid)
  if voter:
    voter.delete()

  if election.frozen_at:
    # log it
    election.append_log("Voter %s/%s removed after election frozen" % (voter.voter_type,voter.voter_id))
    
  return HttpResponseRedirect(reverse(voters_list_pretty, args=[election.uuid]))

@election_admin(frozen=False)
def one_election_set_reg(request, election):
  """
  Set whether this is open registration or not
  """
  open_p = bool(int(request.GET['open_p']))
  election.openreg = open_p
  election.save()
  
  return HttpResponseRedirect(reverse(voters_list_pretty, args=[election.uuid]))

@election_admin()
def one_election_set_featured(request, election):
  """
  Set whether this is a featured election or not
  """

  user = get_user(request)
  if not security.user_can_feature_election(user, election):
    raise PermissionDenied()

  featured_p = bool(int(request.GET['featured_p']))
  election.featured_p = featured_p
  election.save()
  
  return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))

@election_admin()
def one_election_archive(request, election):
  
  archive_p = request.GET.get('archive_p', True)
  
  if bool(int(archive_p)):
    election.archived_at = datetime.datetime.utcnow()
  else:
    election.archived_at = None
    
  election.save()

  return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))

# changed from admin to view because 
# anyone can see the questions, the administration aspect is now
# built into the page
@election_view()
def one_election_questions(request, election):
  questions_json = utils.to_json(election.questions)
  user = get_user(request)
  admin_p = security.user_can_admin_election(user, election)

  return render_template(request, 'election_questions', {'election': election, 'questions_json' : questions_json, 'admin_p': admin_p})

def _check_eligibility(election, user):
  # prevent password-users from signing up willy-nilly for other elections, doesn't make sense
  if user.user_type == 'password':
    return False

  return election.user_eligible_p(user)

def _register_voter(election, user):
  if not _check_eligibility(election, user):
    return None
    
  return Voter.register_user_in_election(user, election)
    
@election_view()
def one_election_register(request, election):
  if not election.openreg:
    return HttpResponseForbidden('registration is closed for this election')
    
  check_csrf(request)
    
  user = get_user(request)
  voter = Voter.get_by_election_and_user(election, user)
  
  if not voter:
    voter = _register_voter(election, user)
    
  return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))

@election_admin(frozen=False)
def one_election_save_questions(request, election):
  check_csrf(request)
  
  election.questions = utils.from_json(request.POST['questions_json']);
  election.save()

  # always a machine API
  return SUCCESS

@transaction.commit_on_success
@election_admin(frozen=False)
def one_election_freeze(request, election):
  # figure out the number of questions and trustees
  issues = election.issues_before_freeze

  if request.method == "GET":
    return render_template(request, 'election_freeze', {'election': election, 'issues' : issues, 'issues_p' : len(issues) > 0})
  else:
    check_csrf(request)
    
    election.freeze()

    if get_user(request):
      return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))
    else:
      return SUCCESS    

def _check_election_tally_type(election):
  for q in election.questions:
    if q['tally_type'] != "homomorphic":
      return False
  return True

@election_admin(frozen=True)
def one_election_compute_tally(request, election):
  """
  tallying is done all at a time now
  """
  if not _check_election_tally_type(election):
    return HttpResponseRedirect(reverse(one_election_view,args=[election.election_id]))

  if request.method == "GET":
    return render_template(request, 'election_compute_tally', {'election': election})
  
  check_csrf(request)

  if not election.voting_ended_at:
    election.voting_ended_at = datetime.datetime.utcnow()

  election.tallying_started_at = datetime.datetime.utcnow()
  election.save()

  tasks.election_compute_tally.delay(election_id = election.id)

  return HttpResponseRedirect(reverse(one_election_view,args=[election.uuid]))

@trustee_check
def trustee_decrypt_and_prove(request, election, trustee):
  if not _check_election_tally_type(election) or election.encrypted_tally == None:
    return HttpResponseRedirect(reverse(one_election_view,args=[election.uuid]))
    
  return render_template(request, 'trustee_decrypt_and_prove', {'election': election, 'trustee': trustee})
  
@election_view(frozen=True)
def trustee_upload_decryption(request, election, trustee_uuid):
  if not _check_election_tally_type(election) or election.encrypted_tally == None:
    return HttpResponseRedirect(reverse(one_election_view,args=[election.election_id]))

  trustee = Trustee.get_by_election_and_uuid(election, trustee_uuid)

  factors_and_proofs = utils.from_json(request.POST['factors_and_proofs'])
  
  # verify the decryption factors
  trustee.decryption_factors = factors_and_proofs['decryption_factors']
  trustee.decryption_proofs = factors_and_proofs['decryption_proofs']
  
  if trustee.verify_decryption_proofs():
    trustee.save()
    
    try:
      # send a note to admin
      election.admin.send_message("%s - trustee partial decryption" % election.name, "trustee %s (%s) did their partial decryption." % (trustee.name, trustee.email))
    except:
      # ah well
      pass
    
    return SUCCESS
  else:
    return FAILURE
  
@election_admin(frozen=True)
def combine_decryptions(request, election):
  """
  combine trustee decryptions
  """

  election_url = get_election_url(election)

  default_subject = 'Tally released for %s' % election.name
  default_body = render_template_raw(None, 'email/result_body.txt', {
      'election' : election,
      'election_url' : election_url,
      'custom_subject' : default_subject,
      'custom_message': '&lt;YOUR MESSAGE HERE&gt;',
      'voter': {'vote_hash' : '<SMART_TRACKER>',
                'name': '<VOTER_NAME>'}
      })

  if request.method == "GET":
    email_form = forms.TallyNotificationEmailForm(initial= {'subject': default_subject})
  else:
    check_csrf(request)

    email_form = forms.TallyNotificationEmailForm(request.POST)

    if email_form.is_valid():
      election.combine_decryptions()
      election.save()

      # notify voters!
      extra_vars = {
        'custom_subject' : email_form.cleaned_data['subject'],
        'custom_message' : email_form.cleaned_data['body'],
        'election_url' : election_url,
        'election' : election
        }

      # if the user opted for notifying no one, then we skip this step
      if email_form.cleaned_data['send_to'] != 'none':
        # exclude those who have not voted
        if email_form.cleaned_data['send_to'] == 'voted':
          voter_constraints_exclude = {'vote_hash' : None}
        else:
          voter_constraints_exclude = {}
      
        # full-length email
        tasks.voters_email.delay(election_id = election.id,
                                 subject_template = 'email/result_subject.txt',
                                 body_template = 'email/result_body.txt',
                                 extra_vars = extra_vars,
                                 voter_constraints_exclude = voter_constraints_exclude)

      # rapid short-message notification
      # this inherently only applies to those who have voted (for the most part)
      # and this is not configurable, this is ALWAYS sent
      tasks.voters_notify.delay(election_id = election.id,
                                notification_template = 'notification/result.txt',
                                extra_vars = extra_vars)

      return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))

  # if just viewing the form or the form is not valid
  return render_template(request, 'combine_decryptions', {'election': election,
                                                          'email_form' : email_form,
                                                          'default_subject': default_subject,
                                                          'default_body': default_body})


@election_admin(frozen=True)
def one_election_set_result_and_proof(request, election):
  if election.tally_type != "homomorphic" or election.encrypted_tally == None:
    return HttpResponseRedirect(reverse(one_election_view,args=[election.election_id]))

  # FIXME: check csrf
  
  election.result = utils.from_json(request.POST['result'])
  election.result_proof = utils.from_json(request.POST['result_proof'])
  election.save()

  if get_user(request):
    return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))
  else:
    return SUCCESS
  
  
@election_view()
def voters_list_pretty(request, election):
  """
  Show the list of voters
  now using Django pagination
  """

  # for django pagination support
  page = int(request.GET.get('page', 1))
  limit = int(request.GET.get('limit', 50))
  q = request.GET.get('q','')
  
  order_by = 'user__user_id'

  # unless it's by alias, in which case we better go by UUID
  if election.use_voter_aliases:
    order_by = 'alias'

  user = get_user(request)
  admin_p = security.user_can_admin_election(user, election)
  
  # files being processed
  voter_files = election.voterfile_set.all()

  # load a bunch of voters
  voters = Voter.get_by_election(election, order_by=order_by)

  if q != '':
    if election.use_voter_aliases:
      voters = voters.filter(alias__icontains = q)
    else:
      voters = voters.filter(name__icontains = q)

  voter_paginator = Paginator(voters, limit)
  voters_page = voter_paginator.page(page)

  total_voters = voter_paginator.count
    
  return render_template(request, 'voters_list', {'election': election, 'voters_page': voters_page,
                                                  'voters': voters_page.object_list, 'admin_p': admin_p, 
                                                  'email_voters': helios.VOTERS_EMAIL,
                                                  'limit': limit, 'total_voters': total_voters,
                                                  'upload_p': helios.VOTERS_UPLOAD, 'q' : q,
                                                  'voter_files': voter_files})

@election_admin()
def voters_upload(request, election):
  """
  Upload a CSV of password-based voters with
  voter_id, email, name
  
  name and email are needed only if voter_type is static
  """
  if election.frozen_at and not election.openreg:
    raise PermissionDenied()

  if request.method == "GET":
    return render_template(request, 'voters_upload', {'election': election})
    
  if request.method == "POST":
    if bool(request.POST.get('confirm_p', 0)):
      # launch the background task to parse that file
      tasks.voter_file_process.delay(voter_file_id = request.session['voter_file_id'])
      del request.session['voter_file_id']

      return HttpResponseRedirect(reverse(voters_list_pretty, args=[election.uuid]))
    else:
      # we need to confirm
      voters_file = request.FILES['voters_file']
      voter_file_obj = election.add_voters_file(voters_file)

      request.session['voter_file_id'] = voter_file_obj.id

      # import the first few lines to check
      voters = [v for v in voter_file_obj.itervoters()][:5]

      return render_template(request, 'voters_upload_confirm', {'election': election, 'voters': voters})

@election_admin()
def voters_upload_cancel(request, election):
  """
  cancel upload of CSV file
  """
  voter_file_id = request.session.get('voter_file_id', None)
  if voter_file_id:
    vf = VoterFile.objects.get(id = voter_file_id)
    vf.delete()
  del request.session['voter_file_id']

  return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))

@election_admin(frozen=True)
def voters_email(request, election):
  if not helios.VOTERS_EMAIL:
    return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))
  
  voter_id = request.REQUEST.get('voter_id', None)
  voter = Voter.get_by_election_and_voter_id(election, voter_id)
  
  if request.method == "GET":
    email_form = forms.EmailVotersForm(initial={'subject': 'Vote in %s' % election.name})
  else:
    email_form = forms.EmailVotersForm(request.POST)
    
    if email_form.is_valid():
      
      # the client knows to submit only once with a specific voter_id
      subject_template = 'email/vote_subject.txt'
      body_template = 'email/vote_body.txt'

      if email_form.cleaned_data['suppress_election_links']:
        body_template = 'email/vote_body_nolinks.txt'
      
      extra_vars = {
        'custom_subject' : email_form.cleaned_data['subject'],
        'custom_message' : email_form.cleaned_data['body'],
        'election_url' : get_election_url(election),
        'election' : election
        }
        
      voter_constraints_include = None
      voter_constraints_exclude = None

      # exclude those who have not voted
      if email_form.cleaned_data['send_to'] == 'voted':
        voter_constraints_exclude = {'vote_hash' : None}

      # include only those who have not voted
      if email_form.cleaned_data['send_to'] == 'not-voted':
        voter_constraints_include = {'vote_hash': None}

      if voter:
        tasks.single_voter_email.delay(voter_uuid = voter.uuid, subject_template = subject_template, body_template = body_template, extra_vars = extra_vars)
      else:
        tasks.voters_email.delay(election_id = election.id, subject_template = subject_template, body_template = body_template, extra_vars = extra_vars, voter_constraints_include = voter_constraints_include, voter_constraints_exclude = voter_constraints_exclude)

      # this batch process is all async, so we can return a nice note
      return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))
    
  return render_template(request, "voters_email", {'email_form': email_form, 'election': election, 'voter': voter})    

# Individual Voters
@election_view()
@json
def voter_list(request, election):
  # normalize limit
  limit = int(request.GET.get('limit', 500))
  if limit > 500: limit = 500
    
  voters = Voter.get_by_election(election, order_by='uuid', after=request.GET.get('after',None), limit= limit)
  return [v.toJSONDict() for v in voters]
  
@election_view()
@json
def one_voter(request, election, voter_uuid):
  """
  View a single voter's info as JSON.
  """
  voter = Voter.get_by_election_and_uuid(election, voter_uuid)
  return voter.toJSONDict()  

@election_view()
@json
def voter_votes(request, election, voter_uuid):
  """
  all cast votes by a voter
  """
  voter = Voter.get_by_election_and_uuid(election, voter_uuid)
  votes = CastVote.get_by_voter(voter)
  return [v.toJSONDict()  for v in votes]

@election_view()
@json
def voter_last_vote(request, election, voter_uuid):
  """
  all cast votes by a voter
  """
  voter = Voter.get_by_election_and_uuid(election, voter_uuid)
  return voter.last_cast_vote().toJSONDict()

##
## cast ballots
##

@election_view()
@json
def ballot_list(request, election):
  """
  this will order the ballots from most recent to oldest.
  and optionally take a after parameter.
  """
  limit = after = None
  if request.GET.has_key('limit'):
    limit = int(request.GET['limit'])
  if request.GET.has_key('after'):
    after = datetime.datetime.strptime(request.GET['after'], '%Y-%m-%d %H:%M:%S')
    
  voters = Voter.get_by_election(election, cast=True, order_by='cast_at', limit=limit, after=after)
  return [v.last_cast_vote().toJSONDict() for v in voters]




