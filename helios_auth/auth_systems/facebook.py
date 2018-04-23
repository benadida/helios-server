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

from helios_auth import utils

def facebook_url(url, params):
  if params:
    return "https://graph.facebook.com%s?%s" % (url, urllib.urlencode(params))
  else:
    return "https://graph.facebook.com%s" % url

def facebook_get(url, params):
  full_url = facebook_url(url,params)
  try:
    return urllib2.urlopen(full_url).read()
  except urllib2.HTTPError:
    from helios_auth.models import AuthenticationExpired
    raise AuthenticationExpired()

def facebook_post(url, params):
  full_url = facebook_url(url, None)
  return urllib2.urlopen(full_url, urllib.urlencode(params)).read()

def get_auth_url(request, redirect_url):
  request.session['fb_redirect_uri'] = redirect_url
  return facebook_url('/oauth/authorize', {
      'client_id': APP_ID,
      'redirect_uri': redirect_url,
      'scope': 'email,user_groups'})
    
def get_user_info_after_auth(request):
  args = facebook_get('/oauth/access_token', {
      'client_id' : APP_ID,
      'redirect_uri' : request.session['fb_redirect_uri'],
      'client_secret' : API_SECRET,
      'code' : request.GET['code']
      })

  access_token = utils.from_json(args)['access_token']

  info = utils.from_json(facebook_get('/me', {'access_token':access_token}))

  return {'type': 'facebook', 'user_id' : info['id'], 'name': info.get('name'), 'email': info.get('email'), 'info': info, 'token': {'access_token': access_token}}
    
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


##
## eligibility checking
##

# a constraint looks like
# {'group' : {'id': 123, 'name': 'asdfsdf'}}
#
# only the ID matters for checking, the name of the group is cached
# here for ease of display so it doesn't have to be re-queried.

def get_user_groups(user):
  groups_raw = utils.from_json(facebook_get('/me/groups', {'access_token':user.token['access_token']}))
  return groups_raw['data']    

def check_constraint(constraint, user):
  # get the groups for the user
  groups = [group['id'] for group in get_user_groups(user)]

  # check if one of them is the group in the constraint
  try:
    return constraint['group']['id'] in groups
  except:
    # FIXME: be more specific about exception catching
    return False

def generate_constraint(category_id, user):
  """
  generate the proper basic data structure to express a constraint
  based on the category string
  """
  groups = get_user_groups(user)
  the_group = [g for g in groups if g['id'] == category_id][0]

  return {'group': the_group}

def list_categories(user):
  return get_user_groups(user)

def eligibility_category_id(constraint):
  return constraint['group']['id']

def pretty_eligibility(constraint):
  return "Facebook users who are members of the \"%s\" group" % constraint['group']['name']

#
# Election Creation
#

def can_create_election(user_id, user_info):
  return True
