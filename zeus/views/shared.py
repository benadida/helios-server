import json
import base64
import os

from django.http import HttpResponse


def get_randomness(request, *args, **kwargs):
    token = request.GET.get('token', False)
    data = {
        'randomness': base64.b64encode(os.urandom(32))
    }
    if token:
        data['token'] = request.session.get('csrf_token')
    return HttpResponse(json.dumps(data), mimetype="application/json")

