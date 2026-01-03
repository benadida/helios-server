"""
Clever Authentication

"""

import urllib.parse

import requests
from django.conf import settings
from requests.auth import HTTPBasicAuth

# some parameters to indicate that status updating is not possible
STATUS_UPDATES = False

# display tweaks
LOGIN_MESSAGE = "Log in with Clever"

AUTHORIZATION_URL = "https://clever.com/oauth/authorize"
TOKEN_URL = "https://clever.com/oauth/tokens"

def get_auth_url(request, redirect_url):
  request.session['clever-redirect-url'] = redirect_url
  params = {
    'response_type': 'code',
    'redirect_uri': redirect_url,
    'client_id': settings.CLEVER_CLIENT_ID,
    'scope': 'read:students read:teachers read:user_id read:sis',
  }
  return f"{AUTHORIZATION_URL}?{urllib.parse.urlencode(params)}"

def get_user_info_after_auth(request):
  if 'code' not in request.GET:
    return None

  redirect_uri = request.session['clever-redirect-url']
  del request.session['clever-redirect-url']

  code = request.GET['code']

  # Exchange code for token using Basic auth
  token_response = requests.post(
    TOKEN_URL,
    data={
      'code': code,
      'grant_type': 'authorization_code',
      'redirect_uri': redirect_uri,
    },
    auth=HTTPBasicAuth(settings.CLEVER_CLIENT_ID, settings.CLEVER_CLIENT_SECRET),
    headers={'Content-Type': 'application/x-www-form-urlencoded'}
  )

  token_data = token_response.json()
  access_token = token_data['access_token']

  # Get user info
  headers = {'Authorization': f'Bearer {access_token}'}
  user_response = requests.get("https://api.clever.com/me", headers=headers)
  response = user_response.json()

  user_id = response['data']['id']
  user_name = "%s %s" % (response['data']['name']['first'], response['data']['name']['last'])
  user_type = response['type']
  user_district = response['data']['district']
  user_grade = response['data'].get('grade', None)

  return {
    'type': 'clever',
    'user_id': user_id,
    'name': user_name,
    'info': {"district": user_district, "type": user_type, "grade": user_grade},
    'token': {'access_token': access_token}
  }

def do_logout(user):
  """
  logout of Clever
  """
  return None

def update_status(token, message):
  """
  simple update
  """
  pass

def send_message(user_id, name, user_info, subject, body):
  """
  send email to Clever users.
  """
  pass

#
# eligibility
#

def check_constraint(constraint, user):
  if 'grade' not in user.info:
    return False
  return constraint['grade'] == user.info['grade']

def generate_constraint(category, user):
  """
  generate the proper basic data structure to express a constraint
  based on the category string
  """
  return {'grade': category}

def list_categories(user):
  return [{"id": str(g), "name": "Grade %d" % g} for g in range(3, 13)]

def eligibility_category_id(constraint):
  return constraint['grade']

def pretty_eligibility(constraint):
  return "Grade %s" % constraint['grade']


#
# Election Creation
#

def can_create_election(user_id, user_info):
  """
  Teachers only for now
  """
  return user_info['type'] == 'teacher'
