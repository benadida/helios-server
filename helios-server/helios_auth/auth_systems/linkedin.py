"""
LinkedIn Authentication
"""

from oauthclient import client

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from helios_auth import utils

from xml.etree import ElementTree

import logging

from django.conf import settings
API_KEY = settings.LINKEDIN_API_KEY
API_SECRET = settings.LINKEDIN_API_SECRET

# some parameters to indicate that status updating is possible
STATUS_UPDATES = False
STATUS_UPDATE_WORDING_TEMPLATE = "Tweet %s"

OAUTH_PARAMS = {
  'root_url' : 'https://api.linkedin.com/uas',
  'request_token_path' : '/oauth/requestToken',
  'authorize_path' : '/oauth/authorize',
  'authenticate_path' : '/oauth/authenticate',
  'access_token_path': '/oauth/accessToken'
}

def _get_new_client(token=None, token_secret=None):
  if token:
    return client.LoginOAuthClient(API_KEY, API_SECRET, OAUTH_PARAMS, token, token_secret)
  else:
    return client.LoginOAuthClient(API_KEY, API_SECRET, OAUTH_PARAMS)

def _get_client_by_token(token):
  return _get_new_client(token['oauth_token'], token['oauth_token_secret'])

def get_auth_url(request, redirect_url):
  client = _get_new_client()
  try:
    tok = client.get_request_token()
  except:
    return None
  
  request.session['request_token'] = tok
  url = client.get_authenticate_url(tok['oauth_token']) 
  return url
    
def get_user_info_after_auth(request):
  tok = request.session['request_token']
  login_client = _get_client_by_token(tok)
  access_token = login_client.get_access_token(verifier = request.GET.get('oauth_verifier', None))
  request.session['access_token'] = access_token
    
  user_info_xml = ElementTree.fromstring(login_client.oauth_request('http://api.linkedin.com/v1/people/~:(id,first-name,last-name)', args={}, method='GET'))
  
  user_id = user_info_xml.findtext('id')
  first_name = user_info_xml.findtext('first-name')
  last_name = user_info_xml.findtext('last-name')

  return {'type': 'linkedin', 'user_id' : user_id, 'name': "%s %s" % (first_name, last_name), 'info': {}, 'token': access_token}
    

def user_needs_intervention(user_id, user_info, token):
  """
  check to see if user is following the users we need
  """
  return None

def _get_client_by_request(request):
  access_token = request.session['access_token']
  return _get_client_by_token(access_token)
  
def update_status(user_id, user_info, token, message):
  """
  post a message to the auth system's update stream, e.g. twitter stream
  """
  return
  #twitter_client = _get_client_by_token(token)
  #result = twitter_client.oauth_request('http://api.twitter.com/1/statuses/update.json', args={'status': message}, method='POST')

def send_message(user_id, user_name, user_info, subject, body):
  pass

def send_notification(user_id, user_info, message):
  pass



#
# Election Creation
#

def can_create_election(user_id, user_info):
  return True
