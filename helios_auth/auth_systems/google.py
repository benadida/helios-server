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

  redirect_url = request.session['google-redirect-url']
  flow = get_flow(redirect_url)

  # Exchange the authorization code for credentials
  flow.fetch_token(code=request.GET['code'])
  credentials = flow.credentials

  # Verify the ID token and get user info
  # Use the userinfo endpoint instead of decoding id_token manually
  headers = {'Authorization': f'Bearer {credentials.token}'}
  userinfo_response = requests.get(
    'https://www.googleapis.com/oauth2/v3/userinfo',
    headers=headers
  )
  userinfo = userinfo_response.json()

  if not userinfo.get('email_verified'):
    raise Exception("Email verification failed: the email address associated with your Google account is not verified. Please verify your email in your Google account settings and try again.")

  email = userinfo.get('email')
  if not email:
    raise Exception("email address not provided by Google")
  name = userinfo.get('name', email)

  return {'type': 'google', 'user_id': email, 'name': name, 'info': {'email': email}, 'token': {}}

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
