"""
django-rollbar context processor

To install, add the following in your settings.py:
1. add 'rollbar.contrib.django.context_processors.rollbar_settings' to TEMPLATE_CONTEXT_PROCESSORS
2. add a section like this:
ROLLBAR = {
    'client_access_token': 'tokengoeshere',
}
3. you can now access your rollbar settings as rollbar_settings from within your django templates

See README.rst for full installation and configuration instructions.
"""

from django.conf import settings


def rollbar_settings(request):
    """Grabs the rollbar settings to make them available to templates."""
    if not hasattr(settings, 'ROLLBAR'):
        return {}
    return {'rollbar_settings': settings.ROLLBAR}
