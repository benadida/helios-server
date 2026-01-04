"""
Gitlab Authentication

"""

from django.conf import settings
from django.core.mail import send_mail
from requests_oauthlib import OAuth2Session

from helios_auth.utils import format_recipient

# some parameters to indicate that status updating is not possible
STATUS_UPDATES = False

# display tweaks
LOGIN_MESSAGE = "Log in with Gitlab"

AUTHORIZATION_URL = "https://gitlab.com/oauth/authorize"
TOKEN_URL = "https://gitlab.com/oauth/token"

def get_oauth_session(redirect_url=None):
  return OAuth2Session(
    settings.GITLAB_CLIENT_ID,
    redirect_uri=redirect_url,
    scope=['read_user'],
  )

def get_auth_url(request, redirect_url):
  oauth = get_oauth_session(redirect_url)
  authorization_url, state = oauth.authorization_url(AUTHORIZATION_URL)
  request.session['gl_redirect_uri'] = redirect_url
  request.session['gl_oauth_state'] = state
  return authorization_url

def get_user_info_after_auth(request):
  if 'code' not in request.GET:
    return None

  # Verify OAuth state to prevent CSRF attacks
  expected_state = request.session.get('gl_oauth_state')
  actual_state = request.GET.get('state')
  if not expected_state or expected_state != actual_state:
    raise Exception("OAuth state mismatch - possible CSRF attack")

  redirect_uri = request.session.get('gl_redirect_uri')

  # Clean up session data
  for key in ['gl_redirect_uri', 'gl_oauth_state']:
    request.session.pop(key, None)

  oauth = get_oauth_session(redirect_uri)
  oauth.fetch_token(
    TOKEN_URL,
    client_secret=settings.GITLAB_CLIENT_SECRET,
    code=request.GET['code'],
  )

  # Get user info
  response = oauth.get("https://gitlab.com/api/v4/user")
  try:
    response.raise_for_status()
  except Exception as e:
    raise Exception("GitLab user API request failed") from e
  user_data = response.json()
  user_id = user_data['username']
  user_name = user_data['name']
  user_email = user_data['email']

  return {
    'type': 'gitlab',
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
