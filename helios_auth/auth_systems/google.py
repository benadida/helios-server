"""
Google Authentication

"""

import requests
from django.conf import settings
from django.core.mail import send_mail
from google_auth_oauthlib.flow import Flow

from helios_auth.utils import format_recipient

# some parameters to indicate that status updating is not possible
STATUS_UPDATES = False

# display tweaks
LOGIN_MESSAGE = "Log in with my Google Account"

def student_email_allowed(email, verified):
  """Exact domain match, using only Google's verified email information."""
  domain = settings.ALU_STUDENT_DOMAIN
  if verified is not True or not isinstance(email, str) or email.count('@') != 1:
    return False
  local, email_domain = email.rsplit('@', 1)
  return bool(local) and (not domain or email_domain.lower() == domain)

def get_flow(redirect_url=None):
  client_config = {
    "web": {
      "client_id": settings.GOOGLE_CLIENT_ID,
      "client_secret": settings.GOOGLE_CLIENT_SECRET,
      "auth_uri": "https://accounts.google.com/o/oauth2/auth",
      "token_uri": "https://oauth2.googleapis.com/token",
    }
  }
  flow = Flow.from_client_config(
    client_config,
    scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile'],
    redirect_uri=redirect_url
  )
  return flow

def get_auth_url(request, redirect_url):
  flow = get_flow(redirect_url)
  request.session['google-redirect-url'] = redirect_url
  authorization_url, state = flow.authorization_url(
    access_type='offline',
    include_granted_scopes='true'
  )
  request.session['google-oauth-state'] = state
  return authorization_url

def get_user_info_after_auth(request):
  if 'code' not in request.GET:
    return None

  # Verify OAuth state to prevent CSRF attacks
  expected_state = request.session.get('google-oauth-state')
  actual_state = request.GET.get('state')
  if not expected_state or expected_state != actual_state:
    raise Exception("OAuth state mismatch - possible CSRF attack")

  redirect_url = request.session.get('google-redirect-url')

  # Clean up session data
  for key in ['google-redirect-url', 'google-oauth-state']:
    request.session.pop(key, None)

  flow = get_flow(redirect_url)

  # Exchange the authorization code for credentials
  flow.fetch_token(code=request.GET['code'])
  credentials = flow.credentials

  # Verify the ID token and get user info
  # Use the userinfo endpoint instead of decoding id_token manually
  headers = {'Authorization': f'Bearer {credentials.token}'}
  try:
    userinfo_response = requests.get(
      'https://www.googleapis.com/oauth2/v3/userinfo',
      headers=headers,
      timeout=15
    )
    userinfo_response.raise_for_status()
  except requests.RequestException as e:
    raise Exception("Failed to retrieve user info from Google.") from e

  try:
    userinfo = userinfo_response.json()
  except ValueError as e:
    raise Exception("Received invalid user info response from Google.") from e

  # Check email_verified (v3) or verified_email (v2) - Google uses different field names
  email_verified = userinfo.get('email_verified', userinfo.get('verified_email'))
  if email_verified is None:
    raise Exception("Google did not provide email verification status")
  if email_verified is not True:
    raise Exception("Email verification failed: the email address associated with your Google account is not verified. Please verify your email in your Google account settings and try again.")

  email = userinfo.get('email')
  if not email:
    raise Exception("email address not provided by Google")
  if not student_email_allowed(email, email_verified):
    # The existing auth failure page allows retry without creating a user/session.
    return None
  if settings.ALU_STUDENT_DOMAIN:
    email = email.lower()
  name = userinfo.get('name', email)

  return {'type': 'google', 'user_id': email, 'name': name,
          'info': {'email': email, 'email_verified': True}, 'token': {}}

def do_logout(user):
  """
  logout of Google
  """
  return None

def update_status(token, message):
  """
  simple update
  """
  pass

def send_message(user_id, name, user_info, subject, body):
  """
  send email to google users. user_id is the email for google.
  """
  send_mail(subject, body, settings.SERVER_EMAIL, [format_recipient(name, user_id)], fail_silently=False)

def check_constraint(constraint, user_info):
  """
  for eligibility
  """
  pass


#
# Election Creation
#

def can_create_election(user_id, user_info):
  return True
