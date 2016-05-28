"""
Google Authentication

"""

from django.http import *
from django.core.mail import send_mail
from django.conf import settings

import httplib2,json

import sys, os, cgi, urllib, urllib2, re

from oauth2client.client import OAuth2WebServerFlow

# some parameters to indicate that status updating is not possible
STATUS_UPDATES = False

# display tweaks
LOGIN_MESSAGE = "Log in with my Google Account"

def get_flow(redirect_url=None):
  return OAuth2WebServerFlow(client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scope='profile email',
            redirect_uri=redirect_url)

def get_auth_url(request, redirect_url):
  flow = get_flow(redirect_url)

  request.session['google-redirect-url'] = redirect_url
  return flow.step1_get_authorize_url()

def get_user_info_after_auth(request):
  flow = get_flow(request.session['google-redirect-url'])

  if not request.GET.has_key('code'):
    return None
  
  code = request.GET['code']
  credentials = flow.step2_exchange(code)

  # the email address is in the credentials, that's how we make sure it's verified
  id_token = credentials.id_token
  if not id_token['email_verified']:
    raise Exception("email address with Google not verified")
   
  email = id_token['email']

  # get the nice name
  http = httplib2.Http(".cache")
  http = credentials.authorize(http)
  (resp_headers, content) = http.request("https://www.googleapis.com/plus/v1/people/me", "GET")

  response = json.loads(content)

  name = response['displayName']
  
  # watch out, response also contains email addresses, but not sure whether thsoe are verified or not
  # so for email address we will only look at the id_token
  
  return {'type' : 'google', 'user_id': email, 'name': name , 'info': {'email': email}, 'token':{}}
    
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
  send_mail(subject, body, settings.SERVER_EMAIL, ["%s <%s>" % (name, user_id)], fail_silently=False)
  
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
