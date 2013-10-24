from django.http import HttpResponse
import sys

def handler(request, *args, **kwargs):
    exc_type, exc, exc_tb = sys.exc_info()
    data = "403 Forbidden\n"
    data += str(exc.args[0]) if exc is not None and exc.args else ""
    return HttpResponse(data, content_type="text/plain", status=403)
