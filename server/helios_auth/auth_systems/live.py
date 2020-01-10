"""
Windows Live Authentication using oAuth WRAP,
so much like Facebook

# NOT WORKING YET because Windows Live documentation and status is unclear. Is it in beta? I think it is.
"""

import logging

from django.conf import settings
APP_ID = settings.LIVE_APP_ID
APP_SECRET = settings.LIVE_APP_SECRET
  
import urllib.request, urllib.parse, urllib.error, urllib.request, urllib.error, urllib.parse, cgi

# some parameters to indicate that status updating is possible
STATUS_UPDATES = False
# STATUS_UPDATE_WORDING_TEMPLATE = "Send %s to your facebook status"

from helios_auth import utils

def live_url(url, params):
  if params:
    return "https://graph.facebook.com%s?%s" % (url, urllib.parse.urlencode(params))
  else:
    return "https://graph.facebook.com%s" % url

def live_get(url, params):
  full_url = live_url(url,params)
  return urllib.request.urlopen(full_url).read()

def live_post(url, params):
  full_url = live_url(url, None)
  return urllib.request.urlopen(full_url, urllib.parse.urlencode(params)).read()

def get_auth_url(request, redirect_url):
  request.session['live_redirect_uri'] = redirect_url
  return live_url('/oauth/authorize', {
      'client_id': APP_ID,
      'redirect_uri': redirect_url,
      'scope': 'publish_stream'})
    
def get_user_info_after_auth(request):
  args = facebook_get('/oauth/access_token', {
      'client_id' : APP_ID,
      'redirect_uri' : request.session['fb_redirect_uri'],
      'client_secret' : API_SECRET,
      'code' : request.GET['code']
      })

  access_token = cgi.parse_qs(args)['access_token'][0]

  info = utils.from_json(facebook_get('/me', {'access_token':access_token}))

  return {'type': 'facebook', 'user_id' : info['id'], 'name': info['name'], 'info': info, 'token': {'access_token': access_token}}
    
def update_status(user_id, user_info, token, message):
  """
  post a message to the auth system's update stream, e.g. twitter stream
  """
  result = facebook_post('/me/feed', {
      'access_token': token['access_token'],
      'message': message
      })

def send_message(user_id, user_name, user_info, subject, body):
  pass


#
# Election Creation
#

def can_create_election(user_id, user_info):
  return True
