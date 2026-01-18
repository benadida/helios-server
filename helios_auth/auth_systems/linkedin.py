"""
LinkedIn Authentication using OAuth 2.0

"""

from django.conf import settings
from django.core.mail import send_mail
from requests_oauthlib import OAuth2Session

from helios_auth.utils import format_recipient

# some parameters to indicate that status updating is not possible
STATUS_UPDATES = False

# display tweaks
LOGIN_MESSAGE = "Log in with LinkedIn"

AUTHORIZATION_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

def get_oauth_session(redirect_url=None):
  return OAuth2Session(
    settings.LINKEDIN_CLIENT_ID,
    redirect_uri=redirect_url,
    scope='openid profile email',
  )

def get_auth_url(request, redirect_url):
  oauth = get_oauth_session(redirect_url)
  authorization_url, state = oauth.authorization_url(AUTHORIZATION_URL)
  request.session['linkedin_redirect_uri'] = redirect_url
  request.session['linkedin_oauth_state'] = state
  return authorization_url

def get_user_info_after_auth(request):
  if 'code' not in request.GET:
    return None

  # Verify OAuth state to prevent CSRF attacks
  expected_state = request.session.get('linkedin_oauth_state')
  actual_state = request.GET.get('state')
  if not expected_state or expected_state != actual_state:
    raise Exception("OAuth state mismatch - possible CSRF attack")

  redirect_uri = request.session.get('linkedin_redirect_uri')

  # Clean up session data
  for key in ['linkedin_redirect_uri', 'linkedin_oauth_state']:
    request.session.pop(key, None)

  oauth = get_oauth_session(redirect_uri)
  oauth.fetch_token(
    TOKEN_URL,
    client_secret=settings.LINKEDIN_CLIENT_SECRET,
    code=request.GET['code'],
  )

  # Get user info from LinkedIn's OpenID Connect userinfo endpoint
  response = oauth.get("https://api.linkedin.com/v2/userinfo")
  try:
    response.raise_for_status()
  except Exception as e:
    raise Exception("LinkedIn user API request failed") from e

  user_data = response.json()
  user_id = user_data['sub']
  user_name = user_data.get('name', user_id)
  user_email = user_data.get('email')

  if not user_email:
    raise Exception("Email address not available from LinkedIn")

  return {
    'type': 'linkedin',
    'user_id': user_id,
    'name': user_name,
    'info': {'email': user_email},
    'token': {},
  }

def do_logout(user):
  return None

def user_needs_intervention(user_id, user_info, token):
  """
  check to see if user needs intervention
  """
  return None

def update_status(token, message):
  pass

def send_message(user_id, name, user_info, subject, body):
  send_mail(
    subject,
    body,
    settings.SERVER_EMAIL,
    [format_recipient(name, user_info['email'])],
    fail_silently=False,
  )

def check_constraint(eligibility, user_info):
  pass

#
# Election Creation
#
def can_create_election(user_id, user_info):
  return True
