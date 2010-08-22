"""
Facebook Authentication
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

APP_ID = settings.FACEBOOK_APP_ID
API_KEY = settings.FACEBOOK_API_KEY
API_SECRET = settings.FACEBOOK_API_SECRET
  
#from facebookclient import Facebook
import urllib, urllib2, cgi

# some parameters to indicate that status updating is possible
STATUS_UPDATES = True
STATUS_UPDATE_WORDING_TEMPLATE = "Send %s to your facebook status"

from auth import utils

def facebook_url(url, params):
  if params:
    return "https://graph.facebook.com%s?%s" % (url, urllib.urlencode(params))
  else:
    return "https://graph.facebook.com%s" % url

def facebook_get(url, params):
  full_url = facebook_url(url,params)
  return urllib2.urlopen(full_url).read()

def facebook_post(url, params):
  full_url = facebook_url(url, None)
  return urllib2.urlopen(full_url, urllib.urlencode(params)).read()

def get_auth_url(request, redirect_url):
  request.session['fb_redirect_uri'] = redirect_url
  return facebook_url('/oauth/authorize', {
      'client_id': APP_ID,
      'redirect_uri': redirect_url,
      'scope': 'publish_stream,email'})
    
def get_user_info_after_auth(request):
  args = facebook_get('/oauth/access_token', {
      'client_id' : APP_ID,
      'redirect_uri' : request.session['fb_redirect_uri'],
      'client_secret' : API_SECRET,
      'code' : request.GET['code']
      })

  access_token = cgi.parse_qs(args)['access_token'][0]

  info = utils.from_json(facebook_get('/me', {'access_token':access_token}))

  return {'type': 'facebook', 'user_id' : info['id'], 'name': info['name'], 'email': info['email'], 'info': info, 'token': {'access_token': access_token}}
    
def update_status(user_id, user_info, token, message):
  """
  post a message to the auth system's update stream, e.g. twitter stream
  """
  result = facebook_post('/me/feed', {
      'access_token': token['access_token'],
      'message': message
      })

def send_message(user_id, user_name, user_info, subject, body):
  if user_info.has_key('email'):
    send_mail(subject, body, settings.SERVER_EMAIL, ["%s <%s>" % (user_name, user_info['email'])], fail_silently=False)    
