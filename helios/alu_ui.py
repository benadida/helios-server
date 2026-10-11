"""ALU presentation adapters. Casting and proof verification stay in Helios."""
import json
import re
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, JsonResponse
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_GET, require_POST

from helios import utils
from helios.crypto import utils as cryptoutils
from helios.models import CastVote
from helios.security import election_view
from helios_auth.security import get_user
from helios_auth.bridge_protocol import https_origin
from helios_auth.bridge_views import private_response
from helios_auth.security import save_in_session_across_logouts


def public_demo(election):
  # Never proxy a private election or expand the existing election allowlist.
  from helios.bridge_eligibility import bridge_election
  if not bridge_election(election) or election.private_p:
    raise PermissionDenied('Election unavailable.')


@require_GET
@election_view()
def ballot(request, election):
  public_demo(election)
  from helios.alu_management import setup_digest
  raw = utils.to_json(election.toJSONDict(complete=True))
  return private_response(JsonResponse({'raw': raw,
    'fingerprint': cryptoutils.hash_b64(raw),
    'setup_digest': setup_digest(election),
    'open': bool(election.voting_has_started() and not election.voting_has_stopped()),
    'released': bool(election.result_released_at),
    'result': election.result if election.result_released_at else None}))


def exact_keys(value, keys):
  if not isinstance(value, dict) or set(value) != set(keys):
    raise ValueError()


def ciphertext_only(raw, election):
  """Reject audit openings, extra fields, malformed/bound-to-other-election ballots."""
  if not isinstance(raw, str) or len(raw.encode('utf8')) > 262144:
    raise ValueError()
  def unique_object(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
      raise ValueError()
    return result
  vote = json.loads(raw, object_pairs_hook=unique_object)
  exact_keys(vote, ('answers', 'election_uuid', 'election_hash'))
  expected = cryptoutils.hash_b64(utils.to_json(election.toJSONDict(complete=True)))
  if vote['election_uuid'] != election.uuid or vote['election_hash'] != expected:
    raise ValueError()
  answers = vote['answers']
  if not isinstance(answers, list) or len(answers) != len(election.questions):
    raise ValueError()
  def integer(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,2500}', value):
      raise ValueError()
  def proof(p):
    exact_keys(p, ('challenge', 'commitment', 'response'))
    exact_keys(p['commitment'], ('A', 'B'))
    for value in (p['challenge'], p['response'], p['commitment']['A'], p['commitment']['B']):
      integer(value)
  for answer, question in zip(answers, election.questions):
    exact_keys(answer, ('choices', 'individual_proofs', 'overall_proof'))
    n = len(question['answers'])
    if (not isinstance(answer['choices'], list) or len(answer['choices']) != n or
        not isinstance(answer['individual_proofs'], list) or len(answer['individual_proofs']) != n):
      raise ValueError()
    for choice, proofs in zip(answer['choices'], answer['individual_proofs']):
      exact_keys(choice, ('alpha', 'beta'))
      integer(choice['alpha']); integer(choice['beta'])
      if not isinstance(proofs, list) or len(proofs) != 2:
        raise ValueError()
      for p in proofs:
        proof(p)
    overall = answer['overall_proof']
    if question['max'] is None:
      if overall is not None:
        raise ValueError()
    else:
      if not isinstance(overall, list) or len(overall) != question['max'] - question['min'] + 1:
        raise ValueError()
      for p in overall:
        proof(p)
  return raw


@sensitive_post_parameters('encrypted_vote')
@require_POST
@election_view(frozen=True)
def submit(request, election):
  public_demo(election)
  # This top-level, ciphertext-only handoff cannot cast a vote. Explicit same-origin
  # CSRF-protected confirmation and fresh validated shared login are still required.
  if request.headers.get('Origin') != https_origin(settings.ALU_BRIDGE_APP_ORIGIN):
    raise PermissionDenied('Ballot handoff origin rejected.')
  if set(request.POST) != {'encrypted_vote'} or len(request.POST.getlist('encrypted_vote')) != 1:
    raise PermissionDenied('Invalid encrypted ballot.')
  try:
    ciphertext_only(request.POST['encrypted_vote'], election)
  except (ValueError, KeyError, TypeError, RecursionError):
    raise PermissionDenied('Invalid encrypted ballot.') from None
  from helios.views import one_election_cast
  save_in_session_across_logouts(request, 'alu_ui_election', election.uuid)
  # A stale browser login must renew before eligibility is checked. The handoff
  # only saves validated ciphertext; confirmation still checks access and CSRF.
  user = get_user(request)
  if not user:
    save_in_session_across_logouts(request, 'encrypted_vote', request.POST['encrypted_vote'])
    return private_response(HttpResponseRedirect(f'/helios/elections/{election.uuid}/ui/login'))
  response = one_election_cast(request, election_uuid=election.uuid)
  return private_response(response)


@require_GET
@election_view()
def login(request, election):
  public_demo(election)
  if request.session.get('alu_ui_election') != election.uuid or not request.session.get('encrypted_vote'):
    raise PermissionDenied('Start with an encrypted ballot.')
  request.session['alu_return_path'] = f'/helios/elections/{election.uuid}/cast_confirm'
  return private_response(HttpResponseRedirect(f'/auth/alu/start/{election.uuid}/'))


@require_GET
@election_view()
def receipt(request, election, tracker):
  public_demo(election)
  if not re.fullmatch(r'[A-Za-z0-9+/]{43}', tracker):
    raise PermissionDenied('Invalid tracker.')
  cast = CastVote.objects.filter(voter__election=election, vote_hash=tracker).first()
  status = 'missing'
  if cast:
    status = 'invalid' if cast.invalidated_at else ('verified' if cast.verified_at else 'pending')
    if status == 'verified' and cast.voter.vote_hash != tracker:
      status = 'superseded'
  return private_response(JsonResponse({'tracker': tracker, 'status': status,
    'released': bool(election.result_released_at)}))


def return_url(election, tracker=None):
  path = https_origin(settings.ALU_BRIDGE_APP_ORIGIN) + '/vote/' + election.uuid
  return path + ('?' + urlencode({'tracker': tracker}) if tracker else '')
