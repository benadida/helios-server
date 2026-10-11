"""Authenticated ALU setup API. Browser ballots never use this management path."""
import hmac
import hashlib
import datetime
import json
import secrets
import time
import uuid

import requests
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory
from django.views.decorators.http import require_POST

from helios import models, views
from helios import utils
from helios_auth.bridge_protocol import eligible_identity, https_origin
from helios_auth.bridge_views import private_response
from helios_auth.models import User


def live_candidate_counts(election):
  """Private running aggregate; never save it as the election's final tally."""
  if not election.frozen_at or not election.questions:
    return {'positions': None, 'counts_status': 'not_ready'}
  if models.BallotPolicyReview.objects.filter(election=election, decision='pending').exists():
    return {'positions': None, 'counts_status': 'review_needed'}
  trustees = list(election.trustee_set.all())
  # External trustees retain control of their keys. Never bypass their shares.
  if not trustees or any(t.secret_key is None for t in trustees):
    return {'positions': None, 'counts_status': 'keys_unavailable'}
  voters = list(election.voter_set.exclude(vote=None).only('vote', 'vote_hash'))
  fingerprint = hashlib.sha256(json.dumps(sorted(v.vote_hash for v in voters)).encode()).hexdigest()
  key = 'alu-live-counts:' + election.uuid + ':' + fingerprint
  counts = cache.get(key)
  if counts is None:
    counts = [[0 for _ in q['answers']] for q in election.questions]
    if voters:
      tally = election.init_tally()
      for voter in voters:
        tally.add_vote(voter.vote, verify_p=False)  # stored votes have already passed verification
      factors = [tally.decryption_factors_and_proofs(t.secret_key)[0] for t in trustees]
      counts = tally.decrypt_from_factors(factors, election.public_key)
      if any(not isinstance(n, int) or n < 0 for row in counts for n in row):
        raise PermissionDenied('Running vote count could not be computed.')
    cache.set(key, counts, 10)
  return {'counts_status': 'available', 'votes': len(voters), 'positions': [
    {'name': q.get('short_name') or q['question'], 'candidates': [
      {'name': name, 'votes': counts[i][j]} for j, name in enumerate(q['answers'])]}
    for i, q in enumerate(election.questions)]}


def management_identity(data):
  """Helios independently asks Neon-backed ALU code for fresh role authorization."""
  try:
    response = requests.post(https_origin(settings.ALU_BRIDGE_APP_ORIGIN) + '/api/helios/manage-access',
      headers={'Authorization': 'Bearer ' + settings.ALU_BRIDGE_SECRET},
      json={'client_id': settings.ALU_BRIDGE_CLIENT_ID, 'subject': data['subject'],
            'election_id': data['election_id'], 'operation': data['operation']},
      timeout=15, allow_redirects=False)
    result = response.json()
    if not isinstance(result, dict):
      raise ValueError()
    if (response.status_code != 200 or result.get('authorized') is not True or
        result.get('binding') != {key: data[key] for key in ('subject', 'election_id', 'operation')} or
        not eligible_identity(result.get('identity')) or result['identity']['subject'] != data['subject']):
      raise ValueError()
    return result['identity']
  except (requests.RequestException, ValueError, KeyError, TypeError):
    raise PermissionDenied('Committee authorization unavailable.') from None


def text(value, maximum):
  if not isinstance(value, str) or not value.strip() or len(value) > maximum:
    raise ValueError()
  return value.strip()


def questions(data):
  seats = data['seats']
  if not isinstance(seats, list) or not 1 <= len(seats) <= 20:
    raise ValueError()
  result = []
  titles = set()
  for seat in seats:
    if not isinstance(seat, dict):
      raise ValueError()
    title = text(seat['title'], 200)
    names = seat['answers']
    if title in titles or not isinstance(names, list) or not 1 <= len(names) <= 30:
      raise ValueError()
    titles.add(title)
    names = [text(name, 200) for name in names]
    if len(set(names)) != len(names):
      raise ValueError()
    result.append({'question': title, 'short_name': title, 'answers': names,
      'answer_urls': [None] * len(names), 'min': 0, 'max': 1, 'choice_type': 'approval',
      'tally_type': 'homomorphic', 'result_type': 'absolute'})
  return result


def setup_digest(election):
  return hashlib.sha256(utils.to_json({'name': election.name,
    'questions': election.questions, 'starts': str(election.voting_starts_at),
    'ends': str(election.voting_ends_at)}).encode()).hexdigest()


@require_POST
def manage(request):
  # Authenticate BEFORE parsing any body or evaluating subjects. Never log either.
  if (not settings.ALU_BRIDGE_SECRET or not hmac.compare_digest(
      request.headers.get('Authorization', '').encode(), ('Bearer ' + settings.ALU_BRIDGE_SECRET).encode())):
    return private_response(HttpResponse('Unauthorized', status=401))
  try:
    if len(request.body) > 65536:
      raise ValueError()
    def unique_object(pairs):
      result = dict(pairs)
      if len(result) != len(pairs):
        raise ValueError()
      return result
    data = json.loads(request.body, object_pairs_hook=unique_object)
    if not isinstance(data, dict):
      raise ValueError()
    text(data.get('subject'), 100)
    text(data.get('operation'), 20)
    text(data.get('election_id'), 36)
    if data['client_id'] != settings.ALU_BRIDGE_CLIENT_ID:
      raise ValueError()
    election_id = str(uuid.UUID(data['election_id']))
    if election_id != data['election_id']:
      raise ValueError()
    operation = data['operation']
    if operation not in ('create', 'ballot', 'freeze', 'tally', 'combine', 'release', 'stats'):
      raise ValueError()
    if 'start_now' in data and (operation != 'freeze' or type(data['start_now']) is not bool):
      raise ValueError()
    identity = management_identity(data)
    with transaction.atomic():
      # Serialize even the first creation, when no binding row exists to lock.
      lock_id = int.from_bytes(uuid.UUID(election_id).bytes[:8], 'big', signed=True)
      with connection.cursor() as cursor:
        cursor.execute('select pg_advisory_xact_lock(%s)', [lock_id])
      binding = models.AluElectionBinding.objects.select_for_update().filter(uuid=election_id,
        client_id=settings.ALU_BRIDGE_CLIENT_ID).first()
      if operation == 'create' and not binding:
        # Creation owns a new draft only. No global admin flag and no changes to
        # authorized permissions in either application.
        name = text(data['name'], 250)
        if models.Election.objects_with_deleted.filter(uuid=election_id).exists():
          raise PermissionDenied('Election identifier already exists.')
        owner = User.update_or_create('alu', identity['subject'], identity.get('name') or identity['email'],
          {'email': identity['email'].lower(), 'email_verified': True}, {})
        election = models.Election.objects.create(uuid=election_id, short_name='alu-' + election_id,
          name=name, description='ALU testing election. Do not use for a production election.',
          admin=owner, openreg=True, eligibility=[{'auth_system': 'alu'}],
          cast_url=https_origin(settings.SECURE_URL_HOST) + '/helios/elections/' + election_id + '/cast')
        election.generate_trustee(views.ELGAMAL_PARAMS)
        binding = models.AluElectionBinding.objects.create(uuid=election_id, election=election,
          client_id=settings.ALU_BRIDGE_CLIENT_ID)
      if not binding:
        raise PermissionDenied('Election unavailable.')
      election = binding.election
      try:
        actor = User.get_by_type_and_id('alu', identity['subject'])
      except User.DoesNotExist:
        raise PermissionDenied('An existing election permission is required.') from None
      if not views.user_can_admin_election(actor, election):
        raise PermissionDenied('An existing election permission is required.')
      if operation == 'stats':
        return private_response(JsonResponse({'election_id': election_id,
          'votes': election.num_cast_votes, 'pending': election.num_pending_votes,
          **live_candidate_counts(election)}))
      if operation == 'tally' and election.num_pending_votes:
        raise PermissionDenied('Votes are still being checked. Please wait a moment and try again.')
      if operation == 'ballot':
        if election.frozen_at:
          raise PermissionDenied('A frozen ballot cannot be changed.')
        election.questions = questions(data)
        election.name = text(data['name'], 250)
        if 'voting_starts_at' in data or 'voting_ends_at' in data:
          def utc(value):
            parsed = datetime.datetime.fromisoformat(value)
            if parsed.tzinfo is None:
              raise ValueError()
            return parsed.astimezone(datetime.timezone.utc).replace(tzinfo=None)
          start = utc(data['voting_starts_at'])
          end = utc(data['voting_ends_at'])
          if end <= start:
            raise ValueError()
          election.voting_starts_at = start
          election.voting_ends_at = end
        election.save()
        election.append_log('Approved ALU ballot synchronized by ' + actor.user_id)
      elif operation != 'create':
        if operation == 'freeze' and data.get('start_now') and election.voting_has_stopped():
          raise PermissionDenied('Closed voting cannot be reopened.')
        # Reject out-of-order operations before native handlers or expensive work.
        if operation in ('tally', 'combine', 'release') and not election.frozen_at:
          raise PermissionDenied('Freeze the approved ballot before tallying.')
        if operation == 'combine' and (election.encrypted_tally is None or
            (election.result is None and not election.ready_for_decryption_combination())):
          raise PermissionDenied('Verified decryption contributions are not ready.')
        if operation == 'release' and election.result is None:
          raise PermissionDenied('Compute and verify the result before publication.')
        # Delegate to the existing protected Helios workflow. This server request
        # already has Bearer authentication AND a fresh independent capability
        # check, equivalent to API CSRF protection; no browser identity is used.
        if operation == 'freeze' and (not isinstance(data.get('setup_digest'), str) or
            not hmac.compare_digest(data['setup_digest'].encode(), setup_digest(election).encode())):
          raise PermissionDenied('The ballot changed. Review it before freezing.')
        handlers = {'freeze': views.one_election_freeze, 'tally': views.one_election_compute_tally,
          'combine': views.combine_decryptions, 'release': views.release_result}
        csrf = secrets.token_urlsafe(32)
        internal = RequestFactory().post('/', {'csrf_token': csrf})
        internal.session = {'user': {'type': 'alu', 'user_id': actor.user_id},
          'alu_election': election_id, 'alu_access_kind': 'committee',
          'alu_session_expires_at': time.time() + 60, 'csrf_token': csrf}
        already_done = ((operation == 'freeze' and election.frozen_at) or
          (operation == 'tally' and election.tallying_started_at) or
          (operation == 'combine' and election.result) or
          (operation == 'release' and election.result_released_at))
        if not already_done:
          response = handlers[operation](internal, election_uuid=election_id)
          if response.status_code != 302:
            raise PermissionDenied('Election workflow is not ready for this action.')
          election.refresh_from_db()
      if operation == 'freeze' and data.get('start_now'):
        # Native Helios supports an actual start distinct from the frozen schedule.
        # Retrying never moves the actual start or changes the closing deadline.
        if not election.frozen_at:
          raise PermissionDenied('Freeze the approved ballot before opening voting.')
        if not election.voting_started_at and not election.voting_has_started():
          election.voting_started_at = datetime.datetime.utcnow()
          election.save(update_fields=['voting_started_at'])
          election.append_log('Voting opened manually by ' + actor.user_id)
      return private_response(JsonResponse({'election_id': election_id,
        'open': bool(election.voting_has_started() and not election.voting_has_stopped()),
        'voting_started_at': election.voting_started_at.isoformat() + 'Z' if election.voting_started_at else None,
        'frozen': bool(election.frozen_at), 'closed': bool(election.voting_has_stopped()),
        'released': bool(election.result_released_at), 'setup_digest': setup_digest(election)}))
  except PermissionDenied as error:
    messages = {
      'Votes are still being checked. Please wait a moment and try again.': 'Votes are still being checked. Please wait a moment and try again.',
      'Ballots require an explicit election-policy decision before tallying.': 'Some votes need committee review before voting can close.',
      'Voting eligibility could not be checked. Please retry.': 'We could not check student accounts. Please try again shortly.',
      'An existing election permission is required.': 'Your account does not have permission to do this. Ask the election administrator for help.',
    }
    return private_response(JsonResponse({'error': messages.get(str(error), 'This step is not ready yet. Check the election setup and try again.')}, status=403))
  except (ValueError, KeyError, TypeError, RecursionError):
    return private_response(HttpResponse('Invalid election setup request', status=400))
