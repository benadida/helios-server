"""Private metadata probe used by the Cloudflare recovery alarm."""
import hmac

from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET

from .models import VoteVerificationJob


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
        response = JsonResponse({'pending': active.exists(),
            'needs_attention': VoteVerificationJob.objects.filter(state='failed').exists()})
    response['Cache-Control'] = 'no-store'
    return response
