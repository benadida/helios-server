# -*- coding: utf-8 -*-
"""
Helios Django Views

Ben Adida (ben@adida.net)
"""

import csv
import urllib
import os
import base64
import tempfile
import signals
import uuid
import datetime
import json as jsonlib
import json as jsonlib

from django.core.urlresolvers import reverse
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect, HttpResponse, \
    HttpResponseForbidden
from django.utils.encoding import smart_unicode
from django.db import transaction, connection
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.forms import ValidationError

from django.forms.formsets import formset_factory

from heliosauth.auth_systems import AUTH_SYSTEMS, can_list_categories
from heliosauth.models import AuthenticationExpired
from heliosauth import security

from helios.crypto import algs, electionalgs, elgamal
from helios.crypto import utils as cryptoutils
from helios import security
from helios.utils import force_utf8
from heliosauth import views as auth_views
from heliosauth.security import *
from helios import utils as helios_utils
from helios.view_utils import *
from helios import forms
from helios import tasks

from zeus import auth
from django.views.decorators.cache import cache_page

try:
    from collections import OrderedDict
except ImportError:
    from django.utils.datastructures import SortedDict as OrderedDict

from zeus import reports
from django.forms import ValidationError

from helios.security import *
from helios.models import *


# Parameters for everything
ELGAMAL_PARAMS = elgamal.Cryptosystem()

DEFAULT_CRYPTOSYSTEM_PARAMS = getattr(settings,
                                      'HELIOS_CRYPTOSYSTEM_PARAMS', False)

# trying new ones from OlivierP
ELGAMAL_PARAMS.p = DEFAULT_CRYPTOSYSTEM_PARAMS['p']
ELGAMAL_PARAMS.q = DEFAULT_CRYPTOSYSTEM_PARAMS['q']
ELGAMAL_PARAMS.g = DEFAULT_CRYPTOSYSTEM_PARAMS['g']

# object ready for serialization
ELGAMAL_PARAMS_LD_OBJECT = datatypes.LDObject.\
        instantiate(ELGAMAL_PARAMS, datatype='legacy/EGParams')

# single election server? Load the single electionfrom models import Election
from django.conf import settings

def dummy_view(request):
  return HttpResponseRedirect("/")


def get_election_url(election):
  return settings.URL_HOST + reverse(election_shortcut, args=[election.short_name])


def election_shortcut(request, election_short_name):
 election = Election.get_by_short_name(election_short_name)
 if election:
   return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))
 else:
   raise Http404

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

@json
def election_params(request):
  return ELGAMAL_PARAMS_LD_OBJECT.toJSONDict()


@trustee_check
def trustee_keygenerator(request, election, trustee):
  """
  A key generator with the current params, like the trustee home but without a specific election.
  """
  eg_params_json = utils.to_json(ELGAMAL_PARAMS_LD_OBJECT.toJSONDict())

  return render_template(request, "election_keygenerator", {'eg_params_json': eg_params_json, 'election': election, 'trustee': trustee})


@auth.user_required
def elections_voted(request):
  user = get_user(request)
  elections = Election.get_by_user_as_voter(user)

  return render_template(request, "elections_voted", {'elections': elections})



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
                                    mixnet_type='remote').order_by(
                                        '-mix_order')[0]
  except IndexError, e:
      raise PermissionDenied('7')

  return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))


def election_remote_mix(request, election_uuid, mix_key):
  election = Election.objects.get(uuid=election_uuid)

  if not election.zeus_stage == 'MIXING':
      raise PermissionDenied('8')

  if not mix_key or not election.mix_key or not mix_key == election.mix_key:
      raise PermissionDenied('9')

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
    raise PermissionDenied('10')

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
    raise PermissionDenied('11')

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

    return HttpResponse(jsonlib.dumps(stats_data, default=handler),
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

  return HttpResponse(jsonlib.dumps(stats, default=handler),
                      mimetype="application/json")

@election_admin(allow_superadmin=True)
def election_report(request, election, format="html"):

  user = get_user(request)
  if not user.superadmin_p:
    raise PermissionDenied('12')

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

    return HttpResponse(jsonlib.dumps(_reports, default=handler),
                        mimetype="application/json")

  if format == "csv":
    pass

  raise PermissionDenied('13')


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
    writer.writerow(map(force_utf8, [voter.voter_login_id,
                                     voter.voter_email,
                                     voter.voter_name or '',
                                     voter.voter_surname or '',
                                     voter.voter_fathername or '',
                                     voter.voter_mobile or '',
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
        raise PermissionDenied('14')

    election.ecounting_request_send = datetime.datetime.now()
    election.save()
    tasks.election_post_ecounting.delay(election.pk, election.get_ecounting_admin_user())
    return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))


@election_view()
@json
def one_election(request, election):
  if not election:
    raise Http404
  return election.toJSONDict(complete=True)


@election_view()
def one_election_view(request, election):
  user = get_user(request)
  admin_p = security.user_can_admin_election(user, election)
  can_feature_p = security.user_can_feature_election(user, election)

  notregistered = False
  eligible_p = True

  election_url = get_election_url(election)
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
        raise PermissionDenied('15')

  if not voter and not user and not trustee:
    raise PermissionDenied('16')

  # status update message?
  if election.openreg:
    if election.voting_has_started:
      status_update_message = u"Vote in %s" % election.name
    else:
      status_update_message = u"Register to vote in %s" % election.name

  # result!
  if election.result:
    status_update_message = u"Results are in for %s" % election.name

  trustees = Trustee.get_by_election(election)

  return render_template(request, 'election_view',
                         {'election' : election, 'trustees': trustees, 'admin_p': admin_p, 'user': user,
                          'voter': voter, 'votes': votes, 'notregistered': notregistered, 'eligible_p': eligible_p,
                          'can_feature_p': can_feature_p, 'election_url' : election_url,
                          'vote_url': vote_url,
                          'menu_active': 'overview',
                          'trustee': trustee,
                          'test_cookie_url': test_cookie_url})

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
def delete_trustee(request, election):

  election.zeus_election.invalidate_election_public()
  trustee = Trustee.get_by_election_and_uuid(election, request.GET['uuid'])
  if trustee.secret_key:
      raise PermissionDenied('16')

  trustee.delete()
  election.zeus_election.compute_election_public()
  return HttpResponseRedirect(reverse(list_trustees_view, args=[election.uuid]))


@election_view()
def trustee_verify_key(request, election, trustee_uuid):
  if trustee_uuid != request.session.get('helios_trustee_uuid', None):
    raise PermissionDenied('17')

  trustee = Trustee.objects.get(election=election, uuid=trustee_uuid)
  trustee.last_verified_key_at = datetime.datetime.now()
  trustee.save()
  return HttpResponse("OK")


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
      raise PermissionDenied('18')

  return {
    # back to urandom, it's fine
    "randomness" : base64.b64encode(os.urandom(32)),
    "token": request.session.get('csrf_token')
    #"randomness" : base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes)
    }


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
    return HttpResponse(jsonlib.dumps({'audit_id': vote_pk }),
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
    raise PermissionDenied('19')

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
    raise PermissionDenied('20')

  # admin requested mixing to start
  if election.mixing_started:
    raise PermissionDenied('21')

  voter = Voter.get_by_election_and_uuid(election, voter_uuid)
  if not voter:
    raise PermissionDenied('22')

  if voter.excluded_at:
    raise PermissionDenied('23')

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
    raise PermissionDenied('24')

  voter = Voter.get_by_election_and_uuid(election, voter_uuid)
  if voter.castvote_set.count():
      raise PermissionDenied('25')

  if voter:
    voter.delete()

  if election.frozen_at:
    # log it
    election.append_log("Voter %s/%s removed after election frozen" % (voter.voter_type,voter.voter_id))

  return HttpResponseRedirect(reverse(voters_list_pretty, args=[election.uuid]))


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
        raise PermissionDenied('26')

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
        raise PermissionDenied('26')

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

@transaction.commit_on_success
@election_admin(frozen=True)
def one_election_force_end(request, election):
  user = get_user(request)
  if not user.superadmin_p:
    raise PermissionDenied('27')
  election.voting_ends_at = datetime.datetime.now()
  election.save()
  return HttpResponseRedirect(reverse(one_election_view, args=[election.uuid]))

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

@election_admin(frozen=True)
def one_election_compute_tally(request, election):
  """
  tallying is done all at a time now
  """
  if not election.voting_can_stop():
      raise PermissionDenied('28')

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
    raise PermissionDenied('29')

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
      raise PermissionDenied('30')

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

  default_subject = render_template_raw(None, 'email/%s_subject.txt' % template, {
      'custom_subject': "&lt;SUBJECT&gt;"
})
  default_body = render_template_raw(None, 'email/%s_body.txt' % template, {
      'election' : election,
      'election_url' : election_url,
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
