"""
Github Authentication

"""

import httplib2
from django.conf import settings
from django.core.mail import send_mail
from oauth2client.client import OAuth2WebServerFlow

from helios_auth import utils

# some parameters to indicate that status updating is not possible
STATUS_UPDATES = False

# display tweaks
LOGIN_MESSAGE = "Log in with GitHub"

def get_flow(redirect_url=None):
  return OAuth2WebServerFlow(
    client_id=settings.GH_CLIENT_ID,
    client_secret=settings.GH_CLIENT_SECRET,
    scope='read:user user:email',
    auth_uri="https://github.com/login/oauth/authorize",
    token_uri="https://github.com/login/oauth/access_token",
    redirect_uri=redirect_url,
  )

def get_auth_url(request, redirect_url):
  flow = get_flow(redirect_url)
  request.session['gh_redirect_uri'] = redirect_url
  return flow.step1_get_authorize_url()

def get_user_info_after_auth(request):
  redirect_uri = request.session['gh_redirect_uri']
  del request.session['gh_redirect_uri']
  flow = get_flow(redirect_uri)
  if 'code' not in request.GET:
    return None
  code = request.GET['code']
  credentials = flow.step2_exchange(code)

  http = httplib2.Http(".cache")
  http = credentials.authorize(http)
  (_, content) = http.request("https://api.github.com/user", "GET")
  response = utils.from_json(content.decode('utf-8'))
  user_id = response['login']
  user_name = response['name']

  (_, content) = http.request("https://api.github.com/user/emails", "GET")
  response = utils.from_json(content.decode('utf-8'))
  user_email = None
  for email in response:
    if email['verified'] and email['primary']:
      user_email = email['email']
      break
  if not user_email:
    raise Exception("email address with GitHub not verified")

  return {
    'type': 'github',
    'user_id': user_id,
    'name': '%s (%s)' % (user_id, user_name),
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
  return True
