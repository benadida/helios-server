"""
Shibboleth authentication
"""

import os
import urllib

from django.conf import settings

def _get_service_url():
    # FIXME current URL
    from helios_auth.views import after
    from django.conf import settings
    from django.core.urlresolvers import reverse

    return settings.SECURE_URL_HOST + reverse(after)


def get_auth_url(request, redirect_url):
    request.session['shibboleth_redirect_url'] = redirect_url
    return settings.SHIBBOLETH_URL % urllib.quote(_get_service_url())


def get_user_info_after_auth(request):
    if not os.environ[settings.SHIBBOLETH_SESSION_KEY]:
        return None

    user_id = os.environ[settings.SHIBBOLETH_PERSON_KEY]
    email = os.environ[settings.SHIBBOLETH_EMAIL]

    name = ''
    if settings.SHIBBOLETH_FIRST_NAME != '' and settings.SHIBBOLETH_LAST_NAME != '':
        name = "%s %s" % (os.environ[settings.SHIBBOLETH_FIRST_NAME], os.environ[settings.SHIBBOLETH_LAST_NAME])

    return {'type': 'shibboleth', 'user_id': user_id, 'name': name, 'info': {'email': email}, 'token': {}}


def do_logout(user):
    """
    perform logout of Shibboleth by redirecting to the Shibboleth logout URL
    """
    return HttpResponseRedirect(settings.SHIBBOLETH_LOGOUT_URL)


def update_status(token, message):
    """
    simple update
    """
    pass


def send_message(user_id, name, user_info, subject, body):
    """
    send email
    """
    send_mail(subject, body, settings.SERVER_EMAIL, ["%s <%s>" % (name, user_info['email'])], fail_silently=False)


def check_constraint(constraint, user_info):
    """
    for eligibility
    """
    pass
