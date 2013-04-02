# -*- coding: utf-8 -*-
"""
Helios Django Views

Ben Adida (ben@adida.net)
"""

import csv, urllib, os, base64, tempfile

from django.core.urlresolvers import reverse
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.http import *
from django.utils.encoding import smart_str, smart_unicode
from django.db import transaction, connection
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.forms import ValidationError

from zeus.forms import election_form_cls
from django.forms.formsets import formset_factory

from heliosauth.security import *
from heliosauth.auth_systems import AUTH_SYSTEMS, can_list_categories
from heliosauth.models import AuthenticationExpired
from heliosauth.security import get_user, save_in_session_across_logouts

from helios.crypto import algs, electionalgs, elgamal
from helios.crypto import utils as cryptoutils
from helios import security
from helios.utils import force_utf8
from heliosauth import views as auth_views
from helios import utils as helios_utils
from helios.workflows import homomorphic
from helios.workflows import mixnet
from helios.view_utils import *

from django.views.decorators.cache import cache_page

import json as json_module

try:
  from collections import OrderedDict
except ImportError:
  from django.utils.datastructures import SortedDict as OrderedDict

from zeus import reports
from django.forms import ValidationError

import tasks

from security import *

import uuid, datetime

from models import *

import forms, signals

import json as jsonlib


# Parameters for everything
ELGAMAL_PARAMS = elgamal.Cryptosystem()

DEFAULT_CRYPTOSYSTEM_PARAMS = getattr(settings, 'HELIOS_CRYPTOSYSTEM_PARAMS', False)

# trying new ones from OlivierP
ELGAMAL_PARAMS.p = DEFAULT_CRYPTOSYSTEM_PARAMS['p']
ELGAMAL_PARAMS.q = DEFAULT_CRYPTOSYSTEM_PARAMS['q']
ELGAMAL_PARAMS.g = DEFAULT_CRYPTOSYSTEM_PARAMS['g']

# object ready for serialization
ELGAMAL_PARAMS_LD_OBJECT = datatypes.LDObject.instantiate(ELGAMAL_PARAMS, datatype='legacy/EGParams')

# single election server? Load the single electionfrom models import Election
from django.conf import settings

def dummy_view(request):
  return HttpResponseRedirect("/")

def get_election_url(election):
  return settings.URL_HOST + reverse(election_shortcut, args=[election.short_name])

def get_election_badge_url(election):
  return settings.URL_HOST + reverse(election_badge, args=[election.uuid])

def get_election_govote_url(election):
  return settings.URL_HOST + reverse(election_vote_shortcut, args=[election.short_name])

def get_castvote_url(cast_vote):
  return settings.URL_HOST + reverse(castvote_shortcut, args=[cast_vote.vote_tinyhash])

# social buttons
def get_socialbuttons_url(url, text):
  if not text:
    return None

  return "%s%s?%s" % (settings.SOCIALBUTTONS_URL_HOST,
                      reverse(socialbuttons),
                      urllib.urlencode({
        'url' : url,
        'text': text.encode('utf-8')
        }))


##
## remote auth utils

def user_reauth(request, user):
  # FIXME: should we be wary of infinite redirects here, and
  # add a parameter to prevent it? Maybe.
  login_url = "%s%s?%s" % (settings.SECURE_URL_HOST,
                           reverse(auth_views.start, args=[user.user_type]),
                           urllib.urlencode({'return_url':
                                               request.get_full_path()}))
  return HttpResponseRedirect(login_url)

##

# simple static views
def home(request):
  user = get_user(request)
  if user:
    elections = Election.get_by_user_as_admin(user, archived_p = False)
  else:
    return HttpResponseRedirect(reverse('heliosauth.views.login'))
    elections = []

  return render_template(request, "index", {'elections' : elections})

def stats(request):
  return dummy_view(request)
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


##
## simple admin for development
##
def admin_autologin(request):
  if "localhost" not in settings.URL_HOST and "127.0.0.1" not in settings.URL_HOST:
    raise Http404

  users = User.objects.filter(admin_p=True)
  if len(users) == 0:
    return HttpResponse("no admin users!")

  if len(users) == 0:
    return HttpResponse("no users!")

  user = users[0]
  request.session['user'] = {'type' : user.user_type, 'user_id' : user.user_id}
  return HttpResponseRedirect("/")

##
## General election features
##

@json
def election_params(request):
  return ELGAMAL_PARAMS_LD_OBJECT.toJSONDict()

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

# a hidden view behind the shortcut that performs the actual perm check
@election_view()
def _election_vote_shortcut(request, election):
  vote_url = "%s/booth/vote.html?%s" % (settings.SECURE_URL_HOST, urllib.urlencode({
    'token': request.session.get('csrf_token'),
    'election_url' : reverse(one_election, args=[election.uuid])}))

  test_cookie_url = "%s?%s" % (reverse(test_cookie), urllib.urlencode({'continue_url' : vote_url}))

  return HttpResponseRedirect(test_cookie_url)

def election_vote_shortcut(request, election_short_name):
  election = Election.get_by_short_name(election_short_name)
  if election:
    return _election_vote_shortcut(request, election_uuid=election.uuid)
  else:
    raise Http404

@election_view()
def _castvote_shortcut_by_election(request, election, cast_vote):
  return render_template(request, 'castvote', {'cast_vote' : cast_vote, 'vote_content': cast_vote.vote.toJSON(), 'the_voter': cast_vote.voter, 'election': election})

def castvote_shortcut(request, vote_tinyhash):
  try:
    cast_vote = CastVote.objects.get(vote_tinyhash = vote_tinyhash)
  except CastVote.DoesNotExist:
    raise Http404

  return _castvote_shortcut_by_election(request, election_uuid = cast_vote.voter.election.uuid, cast_vote=cast_vote)

@trustee_check
def trustee_keygenerator(request, election, trustee):
  """
  A key generator with the current params, like the trustee home but without a specific election.
  """
  eg_params_json = utils.to_json(ELGAMAL_PARAMS_LD_OBJECT.toJSONDict())

  return render_template(request, "election_keygenerator", {'eg_params_json': eg_params_json, 'election': election, 'trustee': trustee})

@login_required
def elections_administered(request):
  return dummy_view(request)
  if not can_create_election(request):
    return HttpResponseForbidden('only an administrator has elections to administer')

  user = get_user(request)
  elections = Election.get_by_user_as_admin(user)

  return render_template(request, "elections_administered", {'elections': elections})

@login_required
def elections_voted(request):
  user = get_user(request)
  elections = Election.get_by_user_as_voter(user)

  return render_template(request, "elections_voted", {'elections': elections})


@login_required
def election_new(request):

  user = get_user(request)
  institution = user.institution

  # only one election per user
  #if user.election:
    #return HttpResponseRedirect(reverse(one_election_view, args=[user.election.uuid]))

  if not can_create_election(request):
    return HttpResponseForbidden('only an administrator can create an election')

  error = None

  ElectionForm = election_form_cls(user, request.REQUEST.get('election_type'))
  if request.method == "GET":
    election_form = ElectionForm(None, institution,
                                 initial={
                                     'private_p': settings.HELIOS_PRIVATE_DEFAULT
                                 })
  else:
    election_form = ElectionForm(None, institution, request.POST)

    if election_form.is_valid():
      with transaction.commit_on_success():
        election = Election()
        election = election_form.save(election, user.institution, ELGAMAL_PARAMS)
        election.admins.add(user)
        return HttpResponseRedirect(election.questions_url())


  return render_template(request, "election_new", {'election_form': election_form, 'election': None, 'error': error})


@election_admin(frozen=True)
def election_result_file(request, election, name, ext):
  if not election.result:
    raise PermissionDenied()

  # we know csv exists
  # this is ugly, documents generation should be included in celery task
  # and called after result decryption
  if not os.path.exists(election.get_result_file_path('csv', 'csv')):
      election.generate_result_docs()

  if request.GET.get('gen', None):
      election.generate_result_docs()

  fname = election.get_result_file_path(name, ext)
  if not os.path.exists(fname):
    raise Http404

  if settings.USE_X_SENDFILE:
    response = HttpResponse()
    response['Content-Type'] = ''
    response['X-Sendfile'] = fname
    return response
  else:
    zip_data = file(fname, 'r')
    response = HttpResponse(zip_data.read(), mimetype='application/%s' % ext)
    zip_data.close()
    basename = os.path.basename(fname)
    response['Content-Dispotition'] = 'attachment; filename=%s' % basename
    return response

@election_admin(frozen=True)
def election_zeus_proofs(request, election):
  if not election.result:
    raise PermissionDenied()

  if not os.path.exists(election.zeus_proofs_path()):
    election.store_zeus_proofs()

  if settings.USE_X_SENDFILE:
    response = HttpResponse()
    response['Content-Type'] = ''
    response['X-Sendfile'] = election.zeus_proofs_path()
    return response
  else:
    zip_data = file(election.zeus_proofs_path())
    response = HttpResponse(zip_data.read(), mimetype='application/zip')
    zip_data.close()
    response['Content-Dispotition'] = 'attachment; filename=%s_proofs.zip' % election.uuid
    return response

@election_admin(frozen=True)
def election_stop_mixing(request, election):
  if not election.remote_mixnets_finished_at:
    election.remote_mixnets_finished_at = datetime.datetime.now()
    election.save()
    tasks.validate_mixing.delay(election.pk)
  return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))


@election_admin(frozen=True)
def election_remove_last_mix(request, election):
  try:
      mix = election.mixnets.filter(status='finished',
                                    mixnet_type='remote').order_by('-mix_order')[0]
  except IndexError, e:
      raise PermissionDenied

  return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))


def election_remote_mix(request, election_uuid, mix_key):
  election = Election.objects.get(uuid=election_uuid)

  if not election.zeus_stage == 'MIXING':
      raise PermissionDenied

  if not mix_key or not election.mix_key or not mix_key == election.mix_key:
      raise PermissionDenied

  resp = {}
  mixnet = election.get_last_mix()
  if request.method == "GET":
      if settings.USE_X_SENDFILE:
        response = HttpResponse()
        response['Content-Type'] = ''
        response['X-Sendfile'] = mixnet.mix_file.path
        return response
      else:
        response = HttpResponse(mimetype="application/json")
        fp = file(mixnet.mix_file.path)
        response.write(fp.read())
        fp.close()
        return response

  mix_id = "remote mix"
  fd, mix_tmp_file = tempfile.mkstemp(prefix=request.META.get('REMOTE_ADDR', 'UNKNOWN')+'-',
                                      dir=settings.ZEUS_CELERY_TEMPDIR)
  os.write(fd, request.body)
  os.close(fd)
  os.chmod(mix_tmp_file, 0666)
  tasks.add_remote_mix.delay(election.pk, mix_tmp_file, mix_id)

  return HttpResponse(jsonlib.dumps({'status':'processing'}),
                          content_type="application/json")


@election_admin()
def one_election_cancel(request, election):

  if election.canceled_at or election.tallied or election.voting_has_stopped():
    raise PermissionDenied

  if request.method == "GET":
    return render_template(request, 'election_cancel', {'election': election})

  check_csrf(request)

  cancel_msg = request.POST.get('cancel_msg', '')
  cancel_date = datetime.datetime.now()

  election.canceled_at = cancel_date
  election.cancel_msg = cancel_msg

  election.save()
  return HttpResponseRedirect('/admin/')


@election_admin(allow_superadmin=True)
def one_election_set_completed(request, election):
  user = get_user(request)
  admin_p = security.user_can_admin_election(user, election) or user.superadmin_p
  if not user.superadmin_p:
    raise PermissionDenied

  election.is_completed = not election.is_completed
  election.save()

  return HttpResponseRedirect('/admin/')


@election_admin(frozen=True)
def one_election_stats(request, election):
  user = get_user(request)
  admin_p = security.user_can_admin_election(user, election) or user.superadmin_p

  stats_data = {'stats': {'election': list(reports.election_report([election]))[0],
                          'votes': list(reports.election_votes_report([election],
                                                                 False))}}

  if request.GET.get('json', None):
    def handler(obj):
      if hasattr(obj, 'isoformat'):
        return obj.isoformat()
      raise TypeError

    return HttpResponse(json_module.dumps(stats_data, default=handler),
                        mimetype="application/json")

  return render_template(request, "election_stats", {
      'election': election,
      'admin_p': admin_p,
      'user': user,
      'menu_active': 'stats',
      'STATS_UPDATE_INTERVAL': getattr(settings, 'HELIOS_STATS_UPDATE_INTERVAL',
                                      2000)
  })


@cache_page(getattr(settings,'HELIOS_STATS_CACHE_TIMEOUT', 60*10))
def one_election_public_stats(request, election_uuid):
  election = Election.objects.get(uuid=election_uuid, is_completed=True)

  stats = {}
  stats['election'] = list(reports.election_report([election], True, True))
  stats['votes'] = list(reports.election_votes_report([election], True, True))
  stats['results'] = list(reports.election_results_report([election]))

  def handler(obj):
    if hasattr(obj, 'isoformat'):
      return obj.isoformat()
    raise TypeError

  return HttpResponse(json_module.dumps(stats, default=handler),
                      mimetype="application/json")

@election_admin(allow_superadmin=True)
def election_report(request, election, format="html"):

  user = get_user(request)
  if not user.superadmin_p:
    raise PermissionDenied

  reports_list = request.GET.get('report', 'election,voters,votes,results').split(",")

  _reports = OrderedDict()
  if 'election' in reports_list:
    _reports['election'] = list(reports.election_report([election], True, False))
  if 'voters' in reports_list:
    _reports['voters'] = list(reports.election_voters_report([election]))
  if 'votes' in reports_list:
    _reports['votes'] = list(reports.election_votes_report([election], True,
                                                           True))
  if 'results' in reports_list:
    _reports['results'] = list(reports.election_results_report([election]))

  if format == "html":
    return render_template(request, "election_report", {
        'election': election,
        'reports': _reports,
    })

  if format == "json":
    def handler(obj):
      if hasattr(obj, 'isoformat'):
        return obj.isoformat()
      raise TypeError

    return HttpResponse(json_module.dumps(_reports, default=handler),
                        mimetype="application/json")

  if format == "csv":
    pass

  raise PermissionDenied


@election_admin()
@json
def one_election_result(request, election):
    if not election.result:
        raise Http404
    return election.zeus_election.get_results()

@election_admin()
def voters_csv(request, election):
  voters = election.voter_set.all()
  response = HttpResponse(mimetype='text/csv')
  filename = smart_unicode("voters-%s.csv" % election.short_name)
  response['Content-Dispotition'] = 'attachment; filename="%s"' % filename
  writer = csv.writer(response)
  for voter in voters:
    vote_field = u"ΝΑΙ" if voter.castvote_set.count() else u"ΟΧΙ"
    if voter.excluded_at:
        vote_field += u"(ΕΞΑΙΡΕΘΗΚΕ)"
    writer.writerow(map(force_utf8, [voter.voter_email,
                                       voter.voter_name,
                                       voter.voter_surname,
                                       voter.voter_fathername or '',
                                       vote_field
                                   ]))
  return response

@election_admin()
def voters_clear(request, election):
  if election.frozen_at:
    return HttpResponseRedirect(reverse(voters_list_pretty,
                                        args=(election.uuid,)))
  else:
    for voter in election.voter_set.all():
      if not voter.castvote_set.count():
        voter.delete()

  return HttpResponseRedirect(reverse(voters_list_pretty,
                                        args=(election.uuid,)))

@election_admin()
def election_post_ecounting(request, election):
    if not election.result:
        raise PermissionDenied

    election.ecounting_request_send = datetime.datetime.now()
    election.save()
    tasks.election_post_ecounting.delay(election.pk, election.get_ecounting_admin_user())
    return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))

@election_admin()
def one_election_edit(request, election):
  user = get_user(request)
  institution = user.institution
  ElectionForm = election_form_cls(user, election.election_type)

  if not can_create_election(request):
    return HttpResponseForbidden('only an administrator can create an election')

  if election.voting_ended_at:
    return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))

  error = None

  if request.method == "GET":
    election_form = ElectionForm(election, institution, initial={
      'name': election.name,
      'voting_starts_at': election.voting_starts_at,
      'voting_ends_at': election.voting_ends_at,
      'voting_extended_until': election.voting_extended_until,
      'help_phone': election.help_phone,
      'help_email': election.help_email,
      'departments': election.departments_string,
      'trustees': election.trustees_string,
      'eligibles_count': election.eligibles_count,
      'has_department_limit': election.has_department_limit,
      'remote_mix': bool(election.mix_key) or False,
      'description': election.description})
  else:
    election_form = ElectionForm(election, institution, request.POST)

    if election_form.is_valid():
      with transaction.commit_on_success():
        election = election_form.save(election, user.institution, ELGAMAL_PARAMS)
        return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))

  return render_template(request, "election_new", {'election_form' : election_form, 'election' : election, 'error': error})

@election_admin(frozen=False)
def one_election_schedule(request, election):
  return dummy_view(request)
  return HttpResponse("foo")

@election_view()
@json
def one_election(request, election):
  if not election:
    raise Http404
  return election.toJSONDict(complete=True)

@election_view()
def election_badge(request, election):
  return dummy_view(request)
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
  election_badge_url = get_election_badge_url(election)
  status_update_message = None

  vote_url = "%s/booth/vote.html?%s" % (settings.SECURE_URL_HOST, urllib.urlencode({
    'token': request.session.get('csrf_token'),
    'election_url' : reverse(one_election, args=[election.uuid])}))

  test_cookie_url = "%s?%s" % (reverse(test_cookie), urllib.urlencode({'continue_url' : vote_url}))

  voter = get_voter(request, user, election)

  if voter:
    # cast any votes?
    votes = CastVote.get_by_voter(voter)
    if election.frozen_at:
        voter.last_visit = datetime.datetime.now()
        voter.save()
  else:
    votes = None

  trustee = None
  if request.session.get('helios_trustee_uuid', None):
    try:
        trustee = Trustee.objects.get(election=election,
                    uuid=request.session.get('helios_trustee_uuid', None))
    except:
        raise PermissionDenied()

  if not voter and not user and not trustee:
    raise PermissionDenied()

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
  socialbuttons_url = get_socialbuttons_url(election_url, status_update_message)

  trustees = Trustee.get_by_election(election)

  return render_template(request, 'election_view',
                         {'election' : election, 'trustees': trustees, 'admin_p': admin_p, 'user': user,
                          'voter': voter, 'votes': votes, 'notregistered': notregistered, 'eligible_p': eligible_p,
                          'can_feature_p': can_feature_p, 'election_url' : election_url,
                          'vote_url': vote_url, 'election_badge_url' : election_badge_url,
                          'menu_active': 'overview',
                          'trustee': trustee,
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
  return dummy_view(request)
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
  return [t.toJSONDict(complete=True) for t in trustees]

@election_view()
def list_trustees_view(request, election):
  trustees = Trustee.get_by_election(election)
  user = get_user(request)
  admin_p = security.user_can_admin_election(user, election)

  return render_template(request, 'list_trustees', {
      'election': election,
      'trustees': trustees,
      'menu_active': 'trustees',
      'admin_p':admin_p})

@election_admin(frozen=False)
def new_trustee(request, election):
  return dummy_view(request)
  if request.method == "GET":
    return render_template(request, 'new_trustee', {'election' : election})
  else:
    # get the public key and the hash, and add it
    name = request.POST['name']
    email = request.POST['email']

    trustee = Trustee(uuid = str(uuid.uuid1()), election=election, name=name, email=email)
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

  election.zeus_election.invalidate_election_public()
  trustee = Trustee.get_by_election_and_uuid(election, request.GET['uuid'])
  if trustee.secret_key:
      raise PermissionDenied

  trustee.delete()
  election.zeus_election.compute_election_public()
  return HttpResponseRedirect(reverse(list_trustees_view, args=[election.uuid]))


@election_view()
def trustee_verify_key(request, election, trustee_uuid):
  if trustee_uuid != request.session.get('helios_trustee_uuid', None):
    raise PermissionDenied()

  trustee = Trustee.objects.get(election=election, uuid=trustee_uuid)
  trustee.last_verified_key_at = datetime.datetime.now()
  trustee.save()
  return HttpResponse("OK")


def trustee_login(request, election_short_name, trustee_email, trustee_secret):
  election = Election.get_by_short_name(election_short_name)
  clear_previous_logins(request)

  if election:
    trustee = Trustee.get_by_election_and_email(election, trustee_email)

    if trustee:
      if trustee.secret == trustee_secret:
        set_logged_in_trustee(request, trustee)
        return HttpResponseRedirect(reverse(trustee_home, args=[election.uuid, trustee.uuid]))
      else:
        # bad secret, we'll let that redirect to the front page
        pass
    else:
      # no such trustee
      raise Http404

  return HttpResponseRedirect("/")


@election_admin()
def trustee_send_url(request, election, trustee_uuid):
  trustee = Trustee.get_by_election_and_uuid(election, trustee_uuid)
  trustee.send_url_via_mail()
  return HttpResponseRedirect(reverse(list_trustees_view, args = [election.uuid]))


@trustee_check
def trustee_home(request, election, trustee):
  if not trustee.public_key:
    return HttpResponseRedirect(reverse(trustee_keygenerator, args=[election.uuid,
                                                            trustee.uuid]))
  return render_template(request, 'trustee_home', {'election': election, 'trustee':trustee})


@trustee_check
def trustee_check_sk(request, election, trustee):
  return render_template(request, 'trustee_check_sk', {'election': election, 'trustee':trustee})


@trustee_check
def trustee_upload_pk(request, election, trustee):
  if request.method == "POST":
    public_key_and_proof = utils.from_json(request.POST['public_key_json'])
    public_key = algs.EGPublicKey.fromJSONDict(public_key_and_proof['public_key'])
    pok = algs.DLogProof.fromJSONDict(public_key_and_proof['pok'])
    election.add_trustee_pk(trustee, public_key, pok)

    try:
      for admin in election.admins.all():
        admin.send_message("%s - trustee pk upload" % election.name, "trustee %s (%s) uploaded a pk." % (trustee.name, trustee.email))
    except:
      # oh well, no message sent
      pass

  return HttpResponseRedirect(reverse(trustee_home, args=[election.uuid, trustee.uuid]))


##
## Ballot Management
##

@json
@election_view()
def get_randomness(request, election):
  """
  get some randomness to sprinkle into the sjcl entropy pool
  """
  if not request.session.get('helios_trustee_uuid') and not \
    request.session.get('CURRENT_VOTER'):
      raise PermissionDenied

  return {
    # back to urandom, it's fine
    "randomness" : base64.b64encode(os.urandom(32)),
    "token": request.session.get('csrf_token')
    #"randomness" : base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes)
    }

@json
@election_view(frozen=True)
def encrypt_ballot(request, election):
  """
  perform the ballot encryption given answers_json, a JSON'ified list of list of answers
  (list of list because each question could have a list of answers if more than one.)
  """
  return dummy_view(request)
  # FIXME: maybe make this just request.POST at some point?
  answers = utils.from_json(request.REQUEST['answers_json'])
  ev = mixnet.EncryptedVote.fromElectionAndAnswers(election, answers)
  return ev.ld_object.includeRandomness().toJSONDict()

@election_view(frozen=True)
def post_audited_ballot(request, election):
  user = get_user(request)
  voter = get_voter(request, user, election)

  if request.method == "POST":
    raw_vote = request.POST['audited_ballot']
    encrypted_vote = utils.from_json(raw_vote)
    audit_request = utils.from_json(request.session['audit_request'])
    audit_password = request.session['audit_password']
    if not audit_password:
        raise Exception("Auditing with no password")
    # fill in the answers and randomness
    audit_request['answers'][0]['randomness'] = encrypted_vote['answers'][0]['randomness']
    audit_request['answers'][0]['answer'] = [encrypted_vote['answers'][0]['answer'][0]]
    encrypted_vote = electionalgs.EncryptedVote.fromJSONDict(audit_request)
    del request.session['audit_request']
    election.cast_vote(voter, encrypted_vote, audit_password)
    vote_pk = AuditedBallot.objects.filter(voter=voter).order_by('-pk')[0].pk
    return HttpResponse(json_module.dumps({'audit_id': vote_pk }),
                        content_type="application/json")

@election_view(frozen=True)
def one_election_cast(request, election):
  """
  on a GET, this is a cancellation, on a POST it's a cast
  """
  if request.method == "GET":
    return HttpResponseRedirect("%s%s" % (settings.URL_HOST, reverse(one_election_view, args = [election.uuid])))

  check_csrf(request)

  user = get_user(request)
  voter = get_voter(request, user, election)

  if (not election.voting_has_started()) or election.voting_has_stopped():
    raise PermissionDenied

  # if user is not logged in
  # bring back to the confirmation page to let him know
  if not voter:
    return HttpResponseRedirect(reverse(one_election_cast_confirm, args=[election.uuid]))

  encrypted_vote = request.POST['encrypted_vote']
  vote = datatypes.LDObject.fromDict(utils.from_json(encrypted_vote),
        type_hint='phoebus/EncryptedVote').wrapped_obj
  audit_password = request.POST.get('audit_password', None)

  cursor = connection.cursor()
  try:
    cursor.execute("SELECT pg_advisory_lock(1)")
    with transaction.commit_on_success():
      cast_result = election.cast_vote(voter, vote, audit_password)
  finally:
    cursor.execute("SELECT pg_advisory_unlock(1)")

  signature = {'signature': cast_result}

  if 'audit_request' in request.session:
      del request.session['audit_request']

  if signature['signature'].startswith("AUDIT REQUEST"):
    request.session['audit_request'] = encrypted_vote
    request.session['audit_password'] = audit_password
    token = request.session.get('csrf_token')
    return HttpResponse('{"audit": 1, "token":"%s"}' % token,
                        mimetype="application/json")
  else:
    # notify user
    tasks.send_cast_vote_email.delay(election, voter, signature)
    url = "%s%s" % (settings.SECURE_URL_HOST, reverse(one_election_cast_done,
                                                      args=[election.uuid]))
    return HttpResponse('{"cast_url": "%s"}' % url, mimetype="application/json")


@election_view(frozen=True, allow_logins=True)
def voter_quick_login(request, election, voter_uuid, voter_secret):
    return_url = reverse(one_election_view, kwargs={'election_uuid':
                                                    election.uuid})
    clear_previous_logins(request)
    try:
      voter = election.voter_set.get(uuid = voter_uuid,
                                     voter_password = voter_secret)

      request.session['CURRENT_VOTER'] = voter

    except Voter.DoesNotExist:
      return_url = '/' + "?bad_login=%s" % election.uuid

    return HttpResponseRedirect(return_url)

@election_view(allow_logins=True)
def password_voter_login(request, election):
  """
  This is used to log in as a voter for a particular election
  """

  return dummy_view(request)

  # the URL to send the user to after they've logged in
  bad_voter_login = (request.GET.get('bad_voter_login', "0") == "1")
  return_url = request.GET.get('return_url', None)

  if request.method == "GET":
    # if user logged in somehow in the interim, e.g. using the login link for administration,
    # then go!
    if user_can_see_election(request, election):
      return HttpResponseRedirect(reverse(one_election_view, args = [election.uuid]))

    password_login_form = forms.VoterPasswordForm()
    return render_template(request, 'password_voter_login',
                           {'election': election,
                            'return_url' : return_url,
                            'password_login_form': password_login_form,
                            'bad_voter_login' : bad_voter_login})

  login_url = request.REQUEST.get('login_url', None)

  if not login_url:
    # login depending on whether this is a private election
    # cause if it's private the login is happening on the front page
    if election.private_p:
      login_url = reverse(password_voter_login, args=[election.uuid])
    else:
      login_url = reverse(one_election_cast_confirm, args=[election.uuid])

  password_login_form = forms.VoterPasswordForm(request.POST)

  if password_login_form.is_valid():
    try:
      voter = election.voter_set.get(voter_login_id = password_login_form.cleaned_data['voter_id'].strip(),
                                     voter_password = password_login_form.cleaned_data['password'].strip())

      request.session['CURRENT_VOTER'] = voter
    except Voter.DoesNotExist:
      redirect_url = login_url + "?" + urllib.urlencode({
          'bad_voter_login' : '1',
          'return_url' : return_url
          })

      return HttpResponseRedirect(redirect_url)

  return HttpResponseRedirect(return_url)

@election_view(frozen=True)
def one_election_cast_confirm(request, election):
  return dummy_view(request)
  user = get_user(request)

  # if no encrypted vote, the user is reloading this page or otherwise getting here in a bad way
  if not request.session.has_key('encrypted_vote'):
    return HttpResponseRedirect(settings.URL_HOST)

  voter = get_voter(request, user, election)

  # auto-register this person if the election is openreg
  if user and not voter and election.openreg:
    voter = _register_voter(election, user)

  # tallied election, no vote casting
  if election.tallied or election.result:
    return HttpResponseRedirect(settings.URL_HOST)

  encrypted_vote = request.session['encrypted_vote'].strip()
  vote_fingerprint = cryptoutils.hash_b64(encrypted_vote)

  # if this user is a voter, prepare some stuff
  if voter:
    vote = datatypes.LDObject.fromDict(utils.from_json(encrypted_vote),
        type_hint='phoebus/EncryptedVote').wrapped_obj

    # prepare the vote to cast
    cast_vote_params = {
      'vote' : vote,
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

    bad_voter_login = (request.GET.get('bad_voter_login', "0") == "1")

    # status update this vote
    if voter and voter.user.can_update_status():
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

    password_only = False

    if auth_systems == None or 'password' in auth_systems:
      show_password = True
      password_login_form = forms.VoterPasswordForm()

      if auth_systems == ['password']:
        password_only = True
    else:
      show_password = False
      password_login_form = None

    return_url = reverse(one_election_cast_confirm, args=[election.uuid])
    login_box = auth_views.login_box_raw(request, return_url=return_url, auth_systems = auth_systems)

  ## CAST VOTE
  # voting has not started or has ended
  if (not election.voting_has_started()) or election.voting_has_stopped():
    return HttpResponseRedirect(settings.URL_HOST)

  # if user is not logged in
  # bring back to the confirmation page to let him know
  if not voter:
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

@election_view(allow_logins=True)
def one_election_download_signature(request, election, fingerprint):
  vote = CastVote.objects.get(fingerprint=fingerprint)
  response = HttpResponse(content_type='application/binary')
  response['Content-Dispotition'] = 'attachment; filename=signature.txt'
  response.write(vote.signature['signature'])
  return response

@election_view(allow_logins=True)
def one_election_cast_done(request, election):
  """
  This view needs to be loaded because of the IFRAME, but then this causes
  problems if someone clicks "reload". So we need a strategy.
  We store the ballot hash in the session
  """
  user = get_user(request)
  voter = get_voter(request, user, election)

  clear_previous_logins(request)

  if voter:
    votes = CastVote.get_by_voter(voter)
    return HttpResponseRedirect(reverse(one_election_cast_done,
                                        args=[election.uuid]) + "?finger=%s" % votes[0].fingerprint)

  logout = True
  if request.GET.get("finger", None):
    vote = CastVote.objects.get(fingerprint=request.GET.get("finger"))
    return render_template(request, 'cast_done', {'election': election,
                                                  'logout': logout, 'cast_vote': vote},
                           include_user=(not logout))

  return HttpResponseRedirect("/")

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

  user = get_user(request)
  admin_p = security.user_can_admin_election(user, election)
  voter = get_voter(request, user, election)

  if request.GET.has_key('vote_hash'):
    b = AuditedBallot.get(election, request.GET['vote_hash'])
    return HttpResponse(b.raw_vote, mimetype="text/plain")

  after = request.GET.get('after', None)
  offset= int(request.GET.get('offset', 0))
  limit = int(request.GET.get('limit', 100))

  audited_ballots = AuditedBallot.get_by_election(election, after=after, limit=limit+1)
  voter_audited_ballots = AuditedBallot.get_by_election(election,
                                                        extra={'voter':voter})

  more_p = len(audited_ballots) > limit
  if more_p:
    audited_ballots = audited_ballots[0:limit]
    next_after = audited_ballots[limit-1].vote_hash
  else:
    next_after = None

  return render_template(request, 'election_audited_ballots', {
    'menu_active': 'audits',
    'election': election, 'audited_ballots': audited_ballots,
    'voter_audited_ballots': voter_audited_ballots,
    'admin_p': admin_p,
    'next_after': next_after,
    'offset': offset,
    'limit': limit,
    'offset_plus_one': offset+1,
    'offset_plus_limit': offset+limit})

@election_admin()
def voter_exclude(request, election, voter_uuid):

  user = get_user(request)
  admin_p = security.user_can_admin_election(user, election)

  if not election.frozen_at or datetime.datetime.now() <= election.voting_starts_at:
    raise PermissionDenied()

  # admin requested mixing to start
  if election.mixing_started:
    raise PermissionDenied()

  voter = Voter.get_by_election_and_uuid(election, voter_uuid)
  if not voter:
    raise PermissionDenied()

  if voter.excluded_at:
    raise PermissionDenied()

  if request.method == 'POST' and request.POST.get('confirm') == '1':
    election.zeus_election.exclude_voter(voter.uuid,
                                         request.POST.get('reason', ''))
    return HttpResponseRedirect(reverse(voters_list_pretty,
                                        args=[election.uuid]))

  return render_template(request, 'voter_exclude', {
      'election': election,
      'voter_o': voter,
      'menu_active': 'voters',
      'admin_p': admin_p
  })


@election_admin()
def voter_delete(request, election, voter_uuid):
  """
  Two conditions under which a voter can be deleted:
  - election is not frozen or
  - election is open reg
  """
  ## FOR NOW we allow this to see if we can redefine the meaning of "closed reg" to be more flexible
  # if election is frozen and has closed registration
  #if election.frozen_at and (not election.openreg):
  #  raise PermissionDenied()

  if election.tallied or election.mixing_started:
    raise PermissionDenied()

  voter = Voter.get_by_election_and_uuid(election, voter_uuid)
  if voter.castvote_set.count():
      raise PermissionDenied

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
  return dummy_view(request)
  # only allow this for public elections
  if not election.private_p:
    open_p = bool(int(request.GET['open_p']))
    election.openreg = open_p
    election.save()

  return HttpResponseRedirect(reverse(voters_list_pretty, args=[election.uuid]))

@election_admin()
def one_election_set_featured(request, election):
  """
  Set whether this is a featured election or not
  """
  return dummy_view(request)

  user = get_user(request)
  if not security.user_can_feature_election(user, election):
    raise PermissionDenied()

  featured_p = bool(int(request.GET['featured_p']))
  election.featured_p = featured_p
  election.save()

  return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))

@election_admin()
def one_election_archive(request, election):

  return dummy_view(request)
  archive_p = request.GET.get('archive_p', True)

  if bool(int(archive_p)):
    election.archived_at = datetime.datetime.utcnow()
  else:
    election.archived_at = None

  election.save()

  return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))

def check_election_permission(request, election,
                              anon=False, eladmin=True,
                              trustee=True, voter=True):

    is_user = get_user(request)
    is_admin = security.user_can_admin_election(user, election)
    is_trustee = None
    trustee_uuid = request.session.get('helios_trustee_uuid', None)

    try:
        is_trustee = election.trustee_set.objecst.get(uuid=trustee_uuid)
    except Trustee.DoesNotExit:
        pass

    is_voter = get_voter(request, user, election)

    if eladmin and is_admin:
        return is_user, is_admin, is_trustee, is_voter

    if trustee and is_trustee:
        return is_user, is_admin, is_trustee, is_voter

    if voter and not is_voter:
        return is_user, is_admin, is_trustee, is_voter

    if anon:
        return is_user, is_admin, is_trustee, is_voter

    raise PermissionDenied



@election_view(require_type='election')
def one_election_questions(request, election):
  from zeus.forms import QuestionForm, DEFAULT_ANSWERS_COUNT, MAX_QUESTIONS_LIMIT
  if election.election_type == 'election_parties':
      from zeus.forms import PartyForm as QuestionForm

  extra = 1
  if election.questions_data:
    extra = 0

  questions_formset = formset_factory(QuestionForm, extra=extra, can_delete=True,
                                      can_order=True)

  user = get_user(request)
  admin_p = security.user_can_admin_election(user, election)

  if request.method == "POST":
      if not election.can_change_questions():
        raise PermissionDenied

      formset = questions_formset(request.POST)
      if formset.is_valid():
        questions_data = []
        for question in formset.cleaned_data:
          if not question:
              continue

          # force sort of answers by extracting index from answer key.
          # cast answer index to integer, otherwise answer_10 would be placed
          # before answer_2
          answer_index = lambda a: int(a[0].replace('answer_', ''))
          isanswer = lambda a: a[0].startswith('answer_')
          answer_values = filter(isanswer, question.iteritems())
          sorted_answers = sorted(answer_values, key=answer_index)

          answers = [x[1] for x in sorted_answers]
          question['answers'] = answers
          for k in question.keys():
            if k in ['DELETE', 'ORDER']:
              del question[k]

          questions_data.append(question)

        election.questions_data = questions_data
        election.update_answers()
        election.save()

        if election.voter_set.count() == 0:
          return HttpResponseRedirect(reverse(voters_upload,
                                            args=[election.uuid]))
        return HttpResponseRedirect(reverse(one_election_questions,
                                            args=[election.uuid])+"#q1")

  else:
      data = election.questions_data or None
      formset = questions_formset(initial=election.questions_data)

  return render_template(request, 'election_questions', {
    'menu_active': 'candidates',
    'default_answers_count': DEFAULT_ANSWERS_COUNT,
    'formset': formset,
    'max_questions_limit': MAX_QUESTIONS_LIMIT,
    'election': election,
    'admin_p': admin_p})


@election_view(require_type='ecounting')
def one_election_candidates(request, election):
  questions_json = utils.to_json(election.questions)
  user = get_user(request)
  admin_p = security.user_can_admin_election(user, election)
  candidates = [] if not election.questions or len(election.questions) == 0 else\
      election.questions[0]['answers']

  if admin_p and request.method == "POST":
    if not election.can_change_candidates():
        raise PermissionDenied

    questions = []

    fields = ['surname', 'name', 'father_name', 'department']

    surnames = request.POST.getlist('candidates_lastname')
    names = request.POST.getlist('candidates_name')
    fathernames = request.POST.getlist('candidates_fathers_name')
    departments = request.POST.getlist('candidates_department')

    def filled(c):
      return c['name'] or c['surname'] or c['father_name']

    candidates_data = zip(surnames, names, fathernames, departments)
    candidates = filter(filled, [dict(zip(fields, d)) for d in candidates_data])

    error = None
    errors = []
    for cand in candidates:
      for key in cand.keys():
        if not cand[key]:
          error = "Invalid entry"
          errors.append(cand)

    empty_inputs = range(5) if len(candidates) else range(15)

    if error:
      return render_template(request, 'election_candidates', {
        'election': election, 'questions_json' : questions_json,
        'candidates': candidates,
        'error': error,
        'departments': election.departments,
        'empty_inputs': empty_inputs,
        'menu_active': 'candidates',
        'admin_p': admin_p})

    candidates = sorted(candidates, key=lambda c: c['surname'])
    question = {}
    question['answer_urls'] = [None for x in range(len(candidates))]
    question['choice_type'] = 'stv'
    question['question'] = 'Candidates choice'
    question['answers'] = []
    question['result_type'] = 'absolute'
    question['tally_type'] = 'stv'
    questions.append(question)
    election.questions = questions
    election.candidates = candidates
    election.sort_candidates()
    election.save()
    election.update_answers()

    if election.voter_set.count() == 0:
      return HttpResponseRedirect(reverse(voters_upload,
                                        args=[election.uuid]))

    return HttpResponseRedirect(reverse(one_election_view,
                                        args=[election.uuid]))

  empty_inputs = range(5) if len(candidates) else range(15)
  return render_template(request, 'election_candidates', {
    'election': election, 'questions_json' : questions_json,
    'candidates': election.candidates,
    'departments': election.departments,
    'empty_inputs': empty_inputs,
    'menu_active': 'candidates',
    'admin_p': admin_p})

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
  return dummy_view(request)
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
  dummy_view()
  check_csrf(request)
  election.questions = utils.from_json(request.POST['questions_json'])
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
    error = False
    try:
      election.freeze()
    except Exception, e:
      error = str(e)
      return render_template(request, 'election_freeze',
                             {'error': error, 'election': election, 'issues' : issues, 'issues_p' : len(issues) > 0})

    if get_user(request):
      return HttpResponseRedirect(reverse(voters_email, args=[election.uuid]))
    else:
      return SUCCESS

def _check_election_tally_type(election):
  return election.workflow_type in ["homomorphic", "mixnet"]

@election_admin(frozen=True)
def one_election_compute_tally(request, election):
  """
  tallying is done all at a time now
  """
  if not election.voting_can_stop():
      raise PermissionDenied

  if not _check_election_tally_type(election):
    return HttpResponseRedirect(reverse(one_election_view,args=[election.election_id]))

  if request.method == "GET":
    return render_template(request, 'election_compute_tally', {'election': election})

  check_csrf(request)

  if not election.voting_ended_at:
    election.voting_ended_at = datetime.datetime.now()

  election.tallying_started_at = datetime.datetime.now()
  election.save()

  tasks.election_compute_tally.delay(election_id = election.id)

  return HttpResponseRedirect(reverse(one_election_view,args=[election.uuid]))

@trustee_check
def trustee_decrypt_and_prove(request, election, trustee):
  if not _check_election_tally_type(election) or not election.tallied:
    return HttpResponseRedirect(reverse(one_election_view,args=[election.uuid]))

  return render_template(request, 'trustee_decrypt_and_prove', {'election': election, 'trustee': trustee})

@trustee_check
def trustee_download_ciphers(request, election, trustee):
    if not _check_election_tally_type(election) or not election.tallied:
        return HttpResponseRedirect(reverse(one_election_view,args=[election.uuid]))

    return HttpResponse(election.encrypted_tally.toJSON())

@election_view(frozen=True)
def trustee_upload_decryption(request, election, trustee_uuid):
  if not _check_election_tally_type(election) or not election.tallied:
    return FAILURE

  trustee = Trustee.get_by_election_and_uuid(election, trustee_uuid)

  if trustee.decryption_factors and trustee.decryption_proofs:
    raise PermissionDenied

  factors_and_proofs = utils.from_json(request.POST['factors_and_proofs'])

  # verify the decryption factors
  decryption_factors = [[datatypes.LDObject.fromDict(factor, type_hint='core/BigInteger').wrapped_obj for factor in one_q_factors] for one_q_factors in factors_and_proofs['decryption_factors']]

  # each proof needs to be deserialized
  decryption_proofs = [[datatypes.LDObject.fromDict(proof, type_hint='legacy/EGZKProof').wrapped_obj for proof in one_q_proofs] for one_q_proofs in factors_and_proofs['decryption_proofs']]

  tasks.add_trustee_factors.delay(election.pk, trustee.pk, decryption_factors, decryption_proofs)

  return SUCCESS

@election_admin(frozen=True)
def combine_decryptions(request, election):
  """
  combine trustee decryptions
  """
  return HttpResponseRedirect(reverse(one_election_view,args=[election.election_id]))

@election_admin(frozen=True)
def one_election_set_result_and_proof(request, election):
  return dummy_view(request)
  if not election.tallied:
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

  validate_hash = request.GET.get('vote_hash', "").strip()
  hash_invalid = None
  hash_valid = None

  if validate_hash:
    try:
      cast = CastVote.objects.get(verified_at__isnull=False,
                   voter__election=election, vote_hash=validate_hash)
      hash_valid = "1"
    except CastVote.DoesNotExist:
      hash_invalid = "1"


  order_by = 'user__user_id'

  # unless it's by alias, in which case we better go by UUID
  if election.use_voter_aliases:
    order_by = 'alias'

  user = get_user(request)
  admin_p = security.user_can_admin_election(user, election)

  categories = None
  eligibility_category_id = None

  try:
    if admin_p and can_list_categories(user.user_type):
      categories = AUTH_SYSTEMS[user.user_type].list_categories(user)
      eligibility_category_id = election.eligibility_category_id(user.user_type)
  except AuthenticationExpired:
    return user_reauth(request, user)

  # files being processed
  voter_files = election.voterfile_set.all()

  # load a bunch of voters
  # voters = Voter.get_by_election(election, order_by=order_by)
  voters = Voter.objects.filter(election = election).order_by('voter_surname')

  if q != '':
    if election.use_voter_aliases:
      voters = voters.filter(alias__icontains = q)
    else:
      voters = voters.filter(voter_name__icontains = q)

  total_voters = voters.count()
  voters_voted = election.voted_count()

  return render_template(request, 'voters_list',
                         {'election': election,
                          'voters': voters, 'admin_p': admin_p,
                          'request': request,
                          'email_voters': helios.VOTERS_EMAIL,
                          'limit': limit, 'total_voters': total_voters,
                          'upload_p': helios.VOTERS_UPLOAD, 'q' : q,
                          'menu_active': 'voters',
                          'voter_files': voter_files,
                          'voted_count': voters_voted,
                          'hash_valid': hash_valid,
                          'validate_hash': validate_hash,
                          'hash_invalid': hash_invalid,
                          'categories': categories,
                          'eligibility_category_id' : eligibility_category_id})

@election_admin()
def voters_eligibility(request, election):
  """
  set eligibility for voters
  """
  return dummy_view(request)
  user = get_user(request)

  if request.method == "GET":
    # this shouldn't happen, only POSTs
    return HttpResponseRedirect("/")

  # for now, private elections cannot change eligibility
  if election.private_p:
    return HttpResponseRedirect(reverse(voters_list_pretty, args=[election.uuid]))

  # eligibility
  eligibility = request.POST['eligibility']

  if eligibility in ['openreg', 'limitedreg']:
    election.openreg= True

  if eligibility == 'closedreg':
    election.openreg= False

  if eligibility == 'limitedreg':
    # now process the constraint
    category_id = request.POST['category_id']

    constraint = AUTH_SYSTEMS[user.user_type].generate_constraint(category_id, user)
    election.eligibility = [{'auth_system': user.user_type, 'constraint': [constraint]}]
  else:
    election.eligibility = None

  election.save()
  return HttpResponseRedirect(reverse(voters_list_pretty, args=[election.uuid]))


@election_admin()
def voters_upload(request, election):
  """
  Upload a CSV of password-based voters with
  voter_id, email, name

  name and email are needed only if voter_type is static
  """

  ## TRYING this: allowing voters upload by admin when election is frozen
  #if election.frozen_at and not election.openreg:
  #  raise PermissionDenied()

  if election.voting_has_stopped():
      raise PermissionDenied

  if request.method == "GET":
    if 'voter_file_id' in request.session:
        del request.session['voter_file_id']

    return render_template(request, 'voters_upload', {'menu_active': 'voters',
                                                      'admin_p': True,
                                                      'election': election,
                                                      'error': request.GET.get('e',None)})

  if request.method == "POST":
    if bool(request.POST.get('confirm_p', 0)):
      # launch the background task to parse that file
      try:
          voter_file = VoterFile.objects.get(id = request.session['voter_file_id'])
          voter_file.process()
      except VoterFile.DoesNotExist:
          pass
      except KeyError:
          pass

      if 'voter_file_id' in request.session:
          del request.session['voter_file_id']

      if not election.questions or not len(election.questions):
        return HttpResponseRedirect(election.questions_url())

      return HttpResponseRedirect(reverse(voters_list_pretty, args=[election.uuid]))
    else:
      # we need to confirm
      error = None
      if request.FILES.has_key('voters_file'):
        voters_file = request.FILES['voters_file']
        voter_file_obj = election.add_voters_file(voters_file)


        # import the first few lines to check
        voters = []
        try:
          voters = [v for v in voter_file_obj.itervoters()]
        except ValidationError, e:
          if hasattr(e, 'messages') and e.messages:
            error = e.messages[0]
          else:
            error = str(e)
        except Exception, e:
          error = str(e)

        if not error:
            request.session['voter_file_id'] = voter_file_obj.id

        return render_template(request, 'voters_upload_confirm', {'election': election,
                                                                  'voters': voters,
                                                                  'count': len(voters),
                                                                  'admin_p': True,
                                                                  'error': error,
                                                                  'menu_active': 'voters' })
      else:
        return HttpResponseRedirect("%s?%s" % (reverse(voters_upload, args=[election.uuid]),
                    urllib.urlencode({'e':'δεν ορίσατε αρχείο ψηφοφόρων, δοκιμάστε ξανά'})))

@election_admin()
def voters_upload_cancel(request, election):
  """
  cancel upload of CSV file
  """
  voter_file_id = request.session.get('voter_file_id', None)
  if voter_file_id:
    vf = VoterFile.objects.get(id = voter_file_id)
    vf.delete()

  if 'voter_file_id' in request.session:
    del request.session['voter_file_id']

  return HttpResponseRedirect(reverse(voters_upload, args=[election.uuid]))

@election_admin()
def voters_email(request, election):

  user = get_user(request)
  admin_p = security.user_can_admin_election(user, election)

  if not helios.VOTERS_EMAIL:
    return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))

  TEMPLATES = [
    ('vote', _('Time to Vote')),
    ('info', _('Additional Info'))
  ]

  default_template = 'vote'
  if not election.frozen_at:
    TEMPLATES.pop(0)
    default_template = 'info'

  template = request.REQUEST.get('template', default_template)

  if not template in [t[0] for t in TEMPLATES]:
    raise Exception("bad template")

  voter_id = request.REQUEST.get('voter_id', None)

  if voter_id:
    voter = Voter.get_by_election_and_voter_id(election, voter_id)
    if not voter:
      return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))
  else:
    voter = None

  election_url = get_election_url(election)
  election_vote_url = get_election_govote_url(election)

  default_subject = render_template_raw(None, 'email/%s_subject.txt' % template, {
      'custom_subject': "&lt;SUBJECT&gt;"
})
  default_body = render_template_raw(None, 'email/%s_body.txt' % template, {
      'election' : election,
      'election_url' : election_url,
      'election_vote_url' : election_vote_url,
      'custom_subject' : default_subject,
      'custom_message': '&lt;BODY&gt;',
      'voter': {'vote_hash' : '<SMART_TRACKER>',
                'name': '<VOTER_NAME>',
                'voter_name': '<VOTER_NAME>',
                'voter_surname': '<VOTER_SURNAME>',
                'voter_login_id': '<VOTER_LOGIN_ID>',
                'voter_password': '<VOTER_PASSWORD>',
                'audit_passwords': '1',
                'get_audit_passwords': ['pass1', 'pass2', '...'],
                'get_quick_login_url': '<VOTER_LOGIN_URL>',
                'voter_type' : election.voter_set.all()[0].voter_type,
                'election' : election}
      })

  if request.method == "GET":
    email_form = forms.EmailVotersForm()
    email_form.fields['subject'].initial = dict(TEMPLATES)[template]
    if voter:
      email_form.fields['send_to'].widget = email_form.fields['send_to'].hidden_widget()
  else:
    email_form = forms.EmailVotersForm(request.POST)

    if email_form.is_valid():

      # the client knows to submit only once with a specific voter_id
      subject_template = 'email/%s_subject.txt' % template
      body_template = 'email/%s_body.txt' % template

      extra_vars = {
        'custom_subject' : email_form.cleaned_data['subject'],
        'custom_message' : email_form.cleaned_data['body'],
        'election_vote_url' : election_vote_url,
        'election_url' : election_url,
        'election' : election,
        }

      voter_constraints_include = None
      voter_constraints_exclude = None

      if voter:
        tasks.single_voter_email.delay(voter_uuid=voter.uuid,
                                       subject_template=subject_template,
                                       body_template=body_template,
                                       extra_vars=extra_vars)
      else:
        # exclude those who have not voted
        if email_form.cleaned_data['send_to'] == 'voted':
          voter_constraints_exclude = {'vote_hash' : None}

        # include only those who have not voted
        if email_form.cleaned_data['send_to'] == 'not-voted':
          voter_constraints_include = {'vote_hash': None}

        tasks.voters_email.delay(election_id=election.id,
                                 subject_template=subject_template,
                                 body_template=body_template,
                                 extra_vars=extra_vars,
                                 voter_constraints_include=voter_constraints_include,
                                 voter_constraints_exclude=voter_constraints_exclude)

      # this batch process is all async, so we can return a nice note
      messages.info(request, "Η αποστολή των email έχει ξεκινήσει.")

      return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))

  return render_template(request, "voters_email", {
      'email_form': email_form, 'election': election,
      'voter_o': voter,
      'admin_p': admin_p,
      'default_subject': default_subject,
      'default_body' : default_body,
      'template' : template,
      'menu_active': 'voters',
      'templates' : TEMPLATES})

# Individual Voters
@election_view()
@json
def voter_list(request, election):
  # normalize limit
  limit = int(request.GET.get('limit', 500))
  if limit > 500: limit = 500

  voters = Voter.get_by_election(election, order_by='uuid', after=request.GET.get('after',None), limit= limit)
  return [v.ld_object.toDict() for v in voters]

@election_view()
@json
def one_voter(request, election, voter_uuid):
  """
  View a single voter's info as JSON.
  """
  return dummy_view(request)
  voter = Voter.get_by_election_and_uuid(election, voter_uuid)
  if not voter:
    raise Http404
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
  return dummy_view(request)
  limit = after = None
  if request.GET.has_key('limit'):
    limit = int(request.GET['limit'])
  if request.GET.has_key('after'):
    after = datetime.datetime.strptime(request.GET['after'], '%Y-%m-%d %H:%M:%S')

  voters = Voter.get_by_election(election, cast=True, order_by='cast_at', limit=limit, after=after)

  # we explicitly cast this to a short cast vote
  return [v.last_cast_vote().ld_object.short.toDict(complete=True) for v in voters]

