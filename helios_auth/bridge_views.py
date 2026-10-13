import datetime
import hmac
import re
import secrets
import time
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_GET, require_POST

from helios.models import Election, Voter
from helios.security import user_can_admin_election
from helios_auth.bridge_protocol import challenge, digest, eligible_identity, https_origin, sign_request
from helios_auth.models import BridgeLoginRequest, User
from helios_auth.security import check_csrf, get_user


def private_response(response):
  response['Cache-Control'] = 'no-store'
  response['Referrer-Policy'] = 'no-referrer'
  response['X-Content-Type-Options'] = 'nosniff'
  return response


def allowed_election(election_id):
  from helios.bridge_eligibility import bridge_election
  election = Election.get_by_uuid(election_id)
  if 'alu' not in settings.AUTH_ENABLED_SYSTEMS or not election or not bridge_election(election):
    return None
  return election


@require_GET
def start(request, election_id):
  election = allowed_election(election_id)
  if not election:
    return private_response(HttpResponseForbidden('Election unavailable.'))
  if request.session.get('alu_last_start', 0) > time.time() - 2:
    confirmed = request.session.get('alu_confirmed_vote')
    if (isinstance(confirmed, dict) and confirmed.get('election') == election_id and
        request.session.get('alu_ui_election') == election_id and request.session.get('encrypted_vote')):
      # Preserve the login cooldown without stranding an already confirmed vote.
      response = render(request, 'helios_auth/bridge_wait.html', {'election_id': election_id})
      response['Retry-After'] = '2'
      return private_response(response)
    return private_response(HttpResponse('Please retry in a moment.', status=429))
  get_user(request)  # establishes the existing Helios CSRF token
  if not request.session.session_key:
    request.session.create()
  state = secrets.token_urlsafe(32)
  verifier = secrets.token_urlsafe(48)
  expires = int(time.time()) + 300
  BridgeLoginRequest.objects.filter(expires_at__lt=datetime.datetime.utcnow()).delete()
  BridgeLoginRequest.objects.create(state_hash=digest(state),
    session_hash=digest(request.session.session_key), election_id=election_id,
    expires_at=datetime.datetime.utcfromtimestamp(expires))
  path = request.session.pop('alu_return_path', '')
  valid_paths = [f'/helios/elections/{election_id}/{suffix}' for suffix in ('view', 'cast_confirm', 'register')]
  request.session['alu_pending'] = {'state': state, 'verifier': verifier,
    'election_id': election_id, 'expires': expires,
    'return_path': path if path in valid_paths else valid_paths[0]}
  request.session['alu_last_start'] = time.time()
  origin = https_origin(settings.ALU_BRIDGE_APP_ORIGIN)
  callback = https_origin(settings.SECURE_URL_HOST) + '/auth/alu/callback/'
  signed = sign_request({'v': 1, 'client_id': settings.ALU_BRIDGE_CLIENT_ID,
    'election_id': election_id, 'state': state, 'code_challenge': challenge(verifier),
    'redirect_uri': callback, 'exp': expires})
  return private_response(HttpResponseRedirect(origin + '/helios/authorize#' + urlencode({'request': signed})))


@require_GET
def callback(request):
  # Codes are only in the fragment; never sent in URLs, referrers or access logs.
  get_user(request)
  return private_response(render(request, 'helios_auth/bridge_callback.html',
                                  {'csrf_token': request.session['csrf_token']}))


@sensitive_post_parameters('code', 'state', 'csrf_token')
@require_POST
def complete(request):
  if request.headers.get('Origin') != https_origin(settings.SECURE_URL_HOST):
    return private_response(HttpResponseForbidden('Login could not be completed.'))
  check_csrf(request)
  pending = request.session.get('alu_pending')
  state = request.POST.get('state', '')
  code = request.POST.get('code', '')
  if (not pending or pending['expires'] <= time.time() or
      not hmac.compare_digest(state, pending['state']) or
      not re.fullmatch(r'[A-Za-z0-9_-]{43}', code)):
    return private_response(HttpResponseForbidden('Login could not be completed.'))
  election_id = pending['election_id']
  # Lock and consume the browser request BEFORE the network exchange. Concurrent
  # callbacks cannot establish two identities; failures require a fresh request.
  with transaction.atomic():
    row = BridgeLoginRequest.objects.select_for_update().filter(
      state_hash=digest(state), session_hash=digest(request.session.session_key),
      election_id=election_id, consumed_at=None,
      expires_at__gt=datetime.datetime.utcnow()).first()
    if not row:
      return private_response(HttpResponseForbidden('Login could not be completed.'))
    row.consumed_at = datetime.datetime.utcnow()
    row.save(update_fields=['consumed_at'])
  request.session.pop('alu_pending', None)
  try:
    response = requests.post(https_origin(settings.ALU_BRIDGE_APP_ORIGIN) + '/api/helios/exchange',
      headers={'Authorization': 'Bearer ' + settings.ALU_BRIDGE_SECRET},
      json={'code': code, 'state': state, 'verifier': pending['verifier'],
            'client_id': settings.ALU_BRIDGE_CLIENT_ID, 'election_id': election_id},
      timeout=15, allow_redirects=False)
    if response.status_code != 200:
      raise ValueError()
    data = response.json()
    identity = data['identity']
    binding = data['binding']
    expiry = data['session_expires_at']
    access_kind = data['access_kind']
    if (access_kind not in ('voter', 'committee') or not eligible_identity(identity) or binding != {
        'client_id': settings.ALU_BRIDGE_CLIENT_ID, 'election_id': election_id,
        'state': state, 'code_challenge': challenge(pending['verifier'])} or
        not isinstance(expiry, (int, float)) or not time.time() < expiry <= time.time() + 305):
      raise ValueError()
  except (requests.RequestException, ValueError, KeyError, TypeError):
    # Never log exception objects: HTTP errors can contain authentication data.
    return private_response(HttpResponseForbidden('Login could not be completed. Please start again.'))
  election = allowed_election(election_id)
  if not election:
    return private_response(HttpResponseForbidden('Election unavailable.'))
  info = {'email': identity['email'].lower(), 'email_verified': True}
  candidate = User(user_type='alu', user_id=identity['subject'], info=info)
  try:
    existing = User.get_by_type_and_id('alu', identity['subject'])
  except User.DoesNotExist:
    existing = None
  registered = Voter.get_by_election_and_user(election, existing) if existing else None
  administrator = user_can_admin_election(existing, election)
  # Committee codes authenticate only an existing authorized administrator.
  # They cannot enroll a voter or manufacture an administrator grant.
  if access_kind == 'committee' and not administrator:
    return private_response(HttpResponseForbidden('Committee access requires an existing election permission.'))
  if ((election.private_p and not (registered or administrator)) or
      not (registered or administrator or election.user_eligible_p(candidate))):
    return private_response(HttpResponseForbidden('Not eligible for this election.'))
  # update_or_create preserves admin_p and election administrator relationships.
  user = User.update_or_create('alu', identity['subject'],
    str(identity.get('name') or info['email'])[:200], info, {})
  request.session.cycle_key()
  request.session['user'] = {'type': 'alu', 'user_id': user.user_id}
  request.session['alu_election'] = election_id
  request.session['alu_session_expires_at'] = expiry
  request.session['alu_access_kind'] = access_kind
  request.session['csrf_token'] = secrets.token_urlsafe(32)
  request.session.pop('CURRENT_VOTER_ID', None)
  return private_response(JsonResponse({'redirect': pending['return_path']}))
