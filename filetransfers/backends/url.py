from django.http import HttpResponseRedirect
from django.utils.encoding import smart_str

def serve_file(request, file, **kwargs):
    """Serves files by redirecting to file.url (e.g., useful for Amazon S3)"""
    return HttpResponseRedirect(smart_str(file.url))

def public_download_url(file, **kwargs):
    """Directs downloads to file.url (useful for normal file system storage)"""
    return file.url
