from django.conf import settings

def public_download_url(file, **kwargs):
    """
    Directs downloads to a handler at settings.PUBLIC_DOWNLOADS_URL_BASE
    """
    return settings.PUBLIC_DOWNLOADS_URL_BASE + file.name
