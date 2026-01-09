"""
OAuth2 Authentication

"""

import httplib2
from django.conf import settings
from django.core.mail import send_mail
from oauth2client.client import OAuth2WebServerFlow
from django.utils.translation import gettext_lazy as _
from helios_auth import utils

# some parameters to indicate that status updating is not possible
STATUS_UPDATES = False

# display tweaks
LOGIN_MESSAGE = getattr(settings, 'OAUTH_LOGIN_MESSAGE', _("Log in with OAuth"))

CA_CERTS = getattr(settings, 'CA_CERTS', None)

def get_http(cache=None):
    kwargs = {}
    if CA_CERTS:
        kwargs['ca_certs'] = CA_CERTS
    if cache:
        return httplib2.Http(cache, **kwargs)
    return httplib2.Http(**kwargs)


def get_flow(redirect_url=None):
    http = get_http()
    return OAuth2WebServerFlow(
        client_id=settings.OAUTH_CLIENT_ID,
        client_secret=settings.OAUTH_CLIENT_SECRET,
        scope='openid profile email',
        auth_uri=settings.OAUTH_AUTH_URI,
        token_uri=settings.OAUTH_TOKEN_URI,
        redirect_uri=redirect_url,
        http=http
    )

def get_auth_url(request, redirect_url):
    flow = get_flow(redirect_url)
    request.session['oauth_redirect_uri'] = redirect_url
    return flow.step1_get_authorize_url()

def get_user_info_after_auth(request):
    redirect_uri = request.session.get('oauth_redirect_uri')
    if 'oauth_redirect_uri' in request.session:
        del request.session['oauth_redirect_uri']

    flow = get_flow(redirect_uri)
    if 'code' not in request.GET:
        return None

    http = get_http()
    code = request.GET['code']
    credentials = flow.step2_exchange(code, http=http)

    http = get_http(".cache")
    http = credentials.authorize(http)

    (request_response, content) = http.request(settings.OAUTH_USER_INFO_URI, "GET")
    response = utils.from_json(content.decode('utf-8'))

    user_id = response.get('preferred_username', response.get('sub'))
    user_name = response.get('name', user_id)
    user_email = response.get('email')

    return {
        'type': 'oauth',
        'user_id': user_id,
        'name': user_name,
        'info': {'email': user_email},
        'token': {},
    }

def do_logout(user):
  return None

def update_status(token, message):
  pass

def send_message(user_id, name, user_info, subject, body):
  send_mail(
    subject,
    body,
    settings.SERVER_EMAIL,
    ["%s <%s>" % (user_id, user_info['email'])],
    fail_silently=False,
  )

def check_constraint(eligibility, user_info):
  pass

#
# Election Creation
#
def can_create_election(user_id, user_info):
  return getattr(settings, 'OAUTH_CAN_CREATE_ELECTION', True)
