"""Authenticated app-to-Helios submission; no cross-origin browser login."""
import datetime
import hmac
import json
import re
import time

import requests
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST

from helios import datatypes
from helios.models import CastVote, Election, Voter
from helios.alu_ui import ciphertext_only, public_demo
from helios.crypto.utils import hash_b64
from helios.bridge_eligibility import require_voting_access
from helios_auth.bridge_protocol import challenge, eligible_identity, https_origin
from helios_auth.bridge_views import private_response
from helios_auth.models import User


def submission_status(election, subject):
    # A failed verifier or rejected proof must never look like an ordinary wait
    # or a student who has never submitted. Prefer any retained active ballot.
    casts = CastVote.objects.filter(voter__election=election,
        voter__user__user_type='alu', voter__user__user_id=subject).select_related('voter').defer('vote', 'voter__vote')
    cast = casts.filter(invalidated_at=None).order_by('-cast_at', '-pk').first()
    if cast is None:
        cast = casts.order_by('-cast_at', '-pk').first()
    status = 'none'
    if cast:
        if cast.invalidated_at:
            status = 'invalid'
        elif cast.is_quarantined:
            status = 'attention'
        elif cast.verified_at:
            status = 'verified' if cast.voter.vote_hash == cast.vote_hash else 'attention'
        elif getattr(getattr(cast, 'verification_job', None), 'state', None) == 'failed':
            status = 'attention'
        else:
            status = 'pending'
    return {'election_id': election.uuid, 'status': status}


def authenticated(request):
    return bool(settings.ALU_BRIDGE_SECRET) and hmac.compare_digest(
        request.headers.get('Authorization', '').encode(),
        ('Bearer ' + settings.ALU_BRIDGE_SECRET).encode())


@sensitive_post_parameters()
@require_POST
def cast(request, election_uuid):
    if not authenticated(request):
        return private_response(JsonResponse({'error': 'Unauthorized'}, status=401))
    election = Election.get_by_uuid(election_uuid)
    if not election:
        return private_response(JsonResponse({'error': 'Election unavailable'}, status=404))
    try:
        public_demo(election)
        if not settings.ALU_VOTE_VERIFICATION_BACKEND == 'database':
            raise PermissionDenied()
        if len(request.body) > 400000:
            raise ValueError()
        def unique(pairs):
            obj = dict(pairs)
            if len(obj) != len(pairs):
                raise ValueError()
            return obj
        data = json.loads(request.body, object_pairs_hook=unique)
        if (set(data) != {'client_id', 'code', 'state', 'verifier', 'encrypted_vote'} or
                data['client_id'] != settings.ALU_BRIDGE_CLIENT_ID or
                not all(isinstance(data[k], str) and re.fullmatch(pattern, data[k])
                    for k, pattern in [('code', r'[A-Za-z0-9_-]{43}'),
                        ('state', r'[A-Za-z0-9_-]{43}'), ('verifier', r'[A-Za-z0-9_-]{64}')])):
            raise ValueError()
        ciphertext_only(data['encrypted_vote'], election)
        # Consume the existing one-use, session-rechecked PKCE grant. A browser
        # identity, old Helios cookie, or bearer credential alone cannot vote.
        response = requests.post(https_origin(settings.ALU_BRIDGE_APP_ORIGIN) + '/api/helios/exchange',
            headers={'Authorization': 'Bearer ' + settings.ALU_BRIDGE_SECRET},
            json={k: data[k] for k in ('client_id', 'code', 'state', 'verifier')} | {'election_id': election.uuid},
            timeout=15, allow_redirects=False)
        if response.status_code != 200:
            return private_response(JsonResponse({'error': 'Sign in again to submit your vote.'}, status=401))
        grant = response.json()
        identity = grant['identity']
        if (not eligible_identity(identity) or grant['access_kind'] != 'voter' or
                grant['binding'] != {'client_id': data['client_id'], 'election_id': election.uuid,
                    'state': data['state'], 'code_challenge': challenge(data['verifier'])} or
                type(grant['session_expires_at']) not in (int, float) or
                not time.time() < grant['session_expires_at'] <= time.time() + 305):
            raise PermissionDenied()
        user = User.update_or_create('alu', identity['subject'],
            str(identity.get('name') or identity['email'])[:200],
            {'email': identity['email'].lower(), 'email_verified': True}, {})
        request.session['alu_election'] = election.uuid
        request.session['alu_access_kind'] = 'voter'
        request.session['alu_session_expires_at'] = grant['session_expires_at']
        require_voting_access(request, election, user)
        request.session['user'] = {'type': 'alu', 'user_id': user.user_id}
        from .alu_guardrails import AluRequestGuardrails
        limited = AluRequestGuardrails(lambda _: None)(request)
        if limited is not None:
            return private_response(JsonResponse({'error': 'Please wait before retrying your vote.'}, status=limited.status_code))
        with transaction.atomic():
            # Serialize first registration too, before the normal voter lock.
            User.objects.select_for_update().get(pk=user.pk)
            voter = Voter.get_by_election_and_user(election, user)
            if voter:
                Voter.objects.select_for_update().get(pk=voter.pk)
                if voter.castvote_set.filter(invalidated_at=None).exists():
                    return private_response(JsonResponse(submission_status(election, user.user_id)))
            election.refresh_from_db()
            if (not election.frozen_at or not election.voting_has_started() or
                    election.voting_has_stopped() or election.encrypted_tally or election.result):
                return private_response(JsonResponse({'error': 'Voting is closed.'}, status=409))
            if not voter:
                if not election.openreg or not election.user_eligible_p(user):
                    raise PermissionDenied()
                voter = Voter.register_user_in_election(user, election)
            # Recheck live membership at the write, as in the native cast path.
            require_voting_access(request, election, user)
            vote = datatypes.LDObject.fromDict(json.loads(data['encrypted_vote']),
                type_hint='legacy/EncryptedVote').wrapped_obj
            cast_vote = CastVote.objects.create(voter=voter, vote=vote,
                vote_hash=hash_b64(data['encrypted_vote']), cast_at=datetime.datetime.utcnow())
            from helios.vote_verification import schedule_verification
            schedule_verification(cast_vote)
        return private_response(JsonResponse(submission_status(election, user.user_id), status=202))
    except (ValueError, KeyError, TypeError, RecursionError, PermissionDenied):
        return private_response(JsonResponse({'error': 'This vote could not be accepted. Please check your account and election.'}, status=403))
    except requests.RequestException:
        return private_response(JsonResponse({'error': 'Sign-in could not be checked. Please try again.'}, status=503))
