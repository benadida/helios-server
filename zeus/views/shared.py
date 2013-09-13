import json
import base64
import os

from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.context_processors import csrf

@require_http_methods(["GET"])
def get_randomness(request, *args, **kwargs):
    token = request.GET.get('token', False)
    data = {
        'randomness': base64.b64encode(os.urandom(32))
    }
    if token:
        data['token'] = unicode(csrf(request)['csrf_token'])
    return HttpResponse(json.dumps(data), mimetype="application/json")

