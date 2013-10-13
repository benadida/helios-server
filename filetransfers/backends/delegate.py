from django.conf import settings

from filetransfers.api import prepare_upload as delegate

def prepare_upload(*args, **kwargs):
    """Delegates uploads to other backends based on private=False or True"""
    if kwargs['private']:
        kwargs['backend'] = settings.PRIVATE_PREPARE_UPLOAD_BACKEND
    else:
        kwargs['backend'] = settings.PUBLIC_PREPARE_UPLOAD_BACKEND
    return delegate(*args, **kwargs)
