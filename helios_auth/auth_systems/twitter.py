"""
Twitter Authentication
"""

from .oauthclient import client

from django.conf.urls import url
from django.urls import reverse
from django.http import HttpResponseRedirect

from helios_auth import utils

import logging

from django.conf import settings
API_KEY = settings.TWITTER_API_KEY
API_SECRET = settings.TWITTER_API_SECRET
USER_TO_FOLLOW = settings.TWITTER_USER_TO_FOLLOW
REASON_TO_FOLLOW = settings.TWITTER_REASON_TO_FOLLOW
DM_TOKEN = settings.TWITTER_DM_TOKEN

# some parameters to indicate that status updating is possible
STATUS_UPDATES = True
STATUS_UPDATE_WORDING_TEMPLATE = "Tweet %s"
FOLLOW_VIEW_URL_NAME = "auth@twitter@follow"

OAUTH_PARAMS = {
  'root_url' : 'https://twitter.com',
  'request_token_path' : '/oauth/request_token',
  'authorize_path' : '/oauth/authorize',
  'authenticate_path' : '/oauth/authenticate',
  'access_token_path': '/oauth/access_token'
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
  twitter_client = _get_client_by_token(tok)
  access_token = twitter_client.get_access_token()
  request.session['access_token'] = access_token
    
  user_info = utils.from_json(twitter_client.oauth_request('http://api.twitter.com/1/account/verify_credentials.json', args={}, method='GET'))
  
  return {'type': 'twitter', 'user_id' : user_info['screen_name'], 'name': user_info['name'], 'info': user_info, 'token': access_token}
    

def user_needs_intervention(user_id, user_info, token):
  """
  check to see if user is following the users we need
  """
  twitter_client = _get_client_by_token(token)
  friendship = utils.from_json(twitter_client.oauth_request('http://api.twitter.com/1/friendships/exists.json', args={'user_a': user_id, 'user_b': USER_TO_FOLLOW}, method='GET'))
  if friendship:
    return None

  return HttpResponseRedirect(reverse(FOLLOW_VIEW_URL_NAME))

def _get_client_by_request(request):
  access_token = request.session['access_token']
  return _get_client_by_token(access_token)
  
def update_status(user_id, user_info, token, message):
  """
  post a message to the auth system's update stream, e.g. twitter stream
  """
  twitter_client = _get_client_by_token(token)
  result = twitter_client.oauth_request('http://api.twitter.com/1/statuses/update.json', args={'status': message}, method='POST')

def send_message(user_id, user_name, user_info, subject, body):
  pass

def public_url(user_id):
  return "http://twitter.com/%s" % user_id

def send_notification(user_id, user_info, message):
  twitter_client = _get_client_by_token(DM_TOKEN)
  result = twitter_client.oauth_request('http://api.twitter.com/1/direct_messages/new.json', args={'screen_name': user_id, 'text': message}, method='POST')

##
## views
##

def follow_view(request):
  if request.method == "GET":
    from helios_auth.view_utils import render_template
    from helios_auth.views import after
    
    return render_template(request, 'twitter/follow', {'user_to_follow': USER_TO_FOLLOW, 'reason_to_follow' : REASON_TO_FOLLOW})

  if request.method == "POST":
    follow_p = bool(request.POST.get('follow_p',False))
    
    if follow_p:
      from helios_auth.security import get_user

      user = get_user(request)
      twitter_client = _get_client_by_token(user.token)
      result = twitter_client.oauth_request('http://api.twitter.com/1/friendships/create.json', args={'screen_name': USER_TO_FOLLOW}, method='POST')

    from helios_auth.url_names import AUTH_AFTER_INTERVENTION
    return HttpResponseRedirect(reverse(AUTH_AFTER_INTERVENTION))



#
# Election Creation
#

def can_create_election(user_id, user_info):
  return True


urlpatterns = [url(r'^twitter/follow', follow_view, name=FOLLOW_VIEW_URL_NAME)]