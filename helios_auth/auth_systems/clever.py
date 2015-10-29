"""
Clever Authentication

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
LOGIN_MESSAGE = "Log in with Clever"

def get_flow(redirect_url=None):
  return OAuth2WebServerFlow(
    client_id=settings.CLEVER_CLIENT_ID,
    client_secret=settings.CLEVER_CLIENT_SECRET,
    scope='read:students read:teachers read:user_id read:sis',
    auth_uri="https://clever.com/oauth/authorize",
    token_uri="https://clever.com/oauth/tokens",
    redirect_uri=redirect_url)
  
def get_auth_url(request, redirect_url):
  flow = get_flow(redirect_url)

  request.session['clever-redirect-url'] = redirect_url
  return flow.step1_get_authorize_url()

def get_user_info_after_auth(request):
  flow = get_flow(request.session['clever-redirect-url'])
  del request.session['clever-redirect-url']

  code = request.GET['code']
  credentials = flow.step2_exchange(code)

  # at this stage, just an access token

  # get the nice name
  http = httplib2.Http(".cache")
  http = credentials.authorize(http)
  (resp_headers, content) = http.request("https://api.clever.com/me", "GET")

  response = json.loads(content)

  # watch out, response also contains email addresses, but not sure whether thsoe are verified or not
  # so for email address we will only look at the id_token
  
  return {'type' : 'clever', 'user_id': response["data"]["id"], 'name': "" , 'info': {"district": response["data"]["district"], "type": response["data"]["type"]}, 'token':{}}
    
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
  pass
  
def check_constraint(constraint, user_info):
  """
  for eligibility
  """
  pass
