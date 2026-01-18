"""
Github Authentication

"""

from django.conf import settings
from django.core.mail import send_mail
from requests_oauthlib import OAuth2Session

from helios_auth.utils import format_recipient

# some parameters to indicate that status updating is not possible
STATUS_UPDATES = False

# GitHub usernames are case-insensitive
CASE_INSENSITIVE_USER_ID = True

# display tweaks
LOGIN_MESSAGE = "Log in with GitHub"

AUTHORIZATION_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"

def get_oauth_session(redirect_url=None):
  return OAuth2Session(
    settings.GH_CLIENT_ID,
    redirect_uri=redirect_url,
    scope='read:user,user:email',
  )

def get_auth_url(request, redirect_url):
  oauth = get_oauth_session(redirect_url)
  authorization_url, state = oauth.authorization_url(AUTHORIZATION_URL)
  request.session['gh_redirect_uri'] = redirect_url
  request.session['gh_oauth_state'] = state
  return authorization_url

def get_user_info_after_auth(request):
  if 'code' not in request.GET:
    return None

  # Verify OAuth state to prevent CSRF attacks
  expected_state = request.session.get('gh_oauth_state')
  actual_state = request.GET.get('state')
  if not expected_state or expected_state != actual_state:
    raise Exception("OAuth state mismatch - possible CSRF attack")

  redirect_uri = request.session.get('gh_redirect_uri')

  # Clean up session data
  for key in ['gh_redirect_uri', 'gh_oauth_state']:
    request.session.pop(key, None)

  oauth = get_oauth_session(redirect_uri)
  oauth.fetch_token(
    TOKEN_URL,
    client_secret=settings.GH_CLIENT_SECRET,
    code=request.GET['code'],
  )

  # Get user info
  response = oauth.get("https://api.github.com/user")
  try:
    response.raise_for_status()
  except Exception as e:
    raise Exception("GitHub user API request failed") from e
  user_data = response.json()
  user_id = user_data['login']
  user_name = user_data.get('name', user_id)

  # Get user emails
  response = oauth.get("https://api.github.com/user/emails")
  try:
    response.raise_for_status()
  except Exception as e:
    raise Exception("GitHub user emails API request failed") from e
  emails = response.json()
  user_email = None
  for email in emails:
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
    [format_recipient(user_id, user_info['email'])],
    fail_silently=False,
  )

def check_constraint(eligibility, user_info):
  pass

#
# Election Creation
#
def can_create_election(user_id, user_info):
  return True
