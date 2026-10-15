"""Private metadata probe used by the Cloudflare recovery alarm."""
import hmac
import datetime

from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET

from .models import VoteVerificationJob, Election


class ContainerHealthMiddleware:
    """Answer SDK startup probes before HTTPS redirects, on internal hosts only."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (request.method in ('GET', 'HEAD') and request.path == '/' and
                request.get_host() in ('ping', 'containerstarthealthcheck')):
            response = HttpResponse('ready', content_type='text/plain')
            response['Cache-Control'] = 'no-store'
            return response
        return self.get_response(request)


@require_GET
def verification_state(request):
    secret = getattr(settings, 'RECOVERY_SECRET', '')
    if not secret or not hmac.compare_digest(
            request.headers.get('Authorization', ''), 'Bearer ' + secret):
        response = JsonResponse({'error': 'Unauthorized'}, status=401)
    else:
        active = (VoteVerificationJob.objects.filter(state='pending',
            cast_vote__voter__election__deleted_at=None)
            .filter(Q(cast_vote__quarantined_p=False) |
                    Q(cast_vote__released_from_quarantine_at__isnull=False)))
        pending = active.exists()
        attention = VoteVerificationJob.objects.filter(state='failed', cast_vote__voter__election__deleted_at=None).exists()
        now = datetime.datetime.utcnow()
        keep_alive = pending or attention or VoteVerificationJob.objects.filter(state='pending', cast_vote__voter__election__deleted_at=None).exists()
        next_wake = None
        # Helios dates are naive UTC. All elections share the same container.
        for election in Election.objects.filter(frozen_at__isnull=False, result_released_at__isnull=True).only(
                'voting_started_at', 'voting_starts_at', 'voting_ended_at', 'tallying_started_at'):
            start = election.voting_started_at or election.voting_starts_at
            if start is None or election.voting_ended_at or election.tallying_started_at or start <= now + datetime.timedelta(minutes=5):
                keep_alive = True
            elif start:
                wake = int((start - datetime.timedelta(minutes=5)).replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
                next_wake = wake if next_wake is None else min(next_wake, wake)
        response = JsonResponse({'pending': pending, 'needs_attention': attention,
            'keep_alive': keep_alive, 'next_wake_at': next_wake})
    response['Cache-Control'] = 'no-store'
    return response
