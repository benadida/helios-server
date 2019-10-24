"""
Google Authentication

"""

from django.http import *
from django.core.mail import send_mail
from django.conf import settings

import httplib2,json

import sys, os, cgi, urllib.request, urllib.parse, urllib.error, urllib.request, urllib.error, urllib.parse, re

from oauth2client.client import OAuth2WebServerFlow
# from google.appengine.api import memcache

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

  if 'code' not in request.GET:
    return None
  
  code = request.GET['code']
  credentials = flow.step2_exchange(code)

  # the email address is in the credentials, that's how we make sure it's verified
  id_token = credentials.id_token
  if not id_token['email_verified']:
    raise Exception("email address with Google not verified")
   
  email = id_token['email']

  # From https://stackoverflow.com/questions/26607645/what-does-h-httplib2-http-cache-mean 
  # httplib2.Http(".cache") creates an instance of the HTTP() class, and sets the cache parameter to .cache, 
  # meaning that a .cache directory in the current working directory is used for cached data.
  # From the Usage section of the project documentation you can see that the cache is used to 
  # cache responses according to HTTP caching rules; the cache will honour cache headers set on 
  # the response unless you override those headers with corresponding request headers.
  
  # http = httplib2.Http(".cache") creates issues on app engine.  Python 3 runtime does not have memcache?
  # Don't use cache in meantime.

  # get the nice name
  #http = httplib2.Http(".cache")
  http = httplib2.Http()
  http = credentials.authorize(http)
  (resp_headers, content) = http.request("https://people.googleapis.com/v1/people/me?personFields=names", "GET")

  response = json.loads(content)

  name = response['names'][0]['displayName']
  
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
