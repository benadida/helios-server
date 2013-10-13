from django.http import HttpResponse
from django.utils.encoding import smart_str

def prepare_upload(request, url, **kwargs):
    """Directly uploads to the given URL"""
    return url, {}

def serve_file(request, file, save_as, content_type, **kwargs):
    """
    Serves the file in chunks for efficiency reasons, but the transfer still
    goes through Django itself, so it's much worse than using the web server,
    but at least it works with all configurations.
    """
    response = HttpResponse(ChunkedFile(file), content_type=content_type)
    if save_as:
        response['Content-Disposition'] = smart_str(u'attachment; filename=%s' % save_as)
    if file.size is not None:
        response['Content-Length'] = file.size
    return response

def public_download_url(file, **kwargs):
    """No public download URL"""
    return None

class ChunkedFile(object):
    def __init__(self, file):
        self.file = file

    def __iter__(self):
        return self.file.chunks()
