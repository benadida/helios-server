"""
Generic Security -- for the auth system

Ben Adida (ben@adida.net)
"""

# nicely update the wrapper function
from functools import update_wrapper

from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.core.exceptions import *
from django.conf import settings

import oauth

import uuid

from auth.models import *

FIELDS_TO_SAVE = 'FIELDS_TO_SAVE'

## FIXME: oauth is NOT working right now

##
## OAuth and API clients
##

class OAuthDataStore(oauth.OAuthDataStore):
  def __init__(self):
    pass
      
  def lookup_consumer(self, key):
    c = APIClient.objects.get(consumer_key = key)
    return oauth.OAuthConsumer(c.consumer_key, c.consumer_secret)

  def lookup_token(self, oauth_consumer, token_type, token):
    if token_type != 'access':
      raise NotImplementedError

    c = APIClient.objects.get(consumer_key = oauth_consumer.key)
    return oauth.OAuthToken(c.consumer_key, c.consumer_secret)

  def lookup_nonce(self, oauth_consumer, oauth_token, nonce):
    """
    FIXME this to actually check for nonces
    """
    return None

# create the oauth server
OAUTH_SERVER = oauth.OAuthServer(OAuthDataStore())
OAUTH_SERVER.add_signature_method(oauth.OAuthSignatureMethod_HMAC_SHA1())
    
def get_api_client(request):
  parameters = request.POST.copy()
  parameters.update(request.GET)
  
  full_url = request.get_full_path()
    
  oauth_request = oauth.OAuthRequest.from_request(request.method, full_url, headers= request.META,
                                                  parameters=parameters, query_string=None)
                                                  
  if not oauth_request:
    return None
    
  try:
    consumer, token, params = OAUTH_SERVER.verify_request(oauth_request)
    return APIClient.objects.get(consumer_key = consumer.key)
  except oauth.OAuthError:
    return None
  
# decorator for login required
def login_required(func):
  def login_required_wrapper(request, *args, **kw):
    if not (get_user(request) or get_api_client(request)):
      return HttpResponseRedirect(settings.LOGIN_URL + "?return_url=" + request.get_full_path())
  
    return func(request, *args, **kw)

  return update_wrapper(login_required_wrapper, func)
  
# decorator for admin required
def admin_required(func):
  def admin_required_wrapper(request, *args, **kw):
    user = get_user(request)
    if not user or not user.is_staff:
      raise PermissionDenied()
      
    return func(request, *args, **kw)

  return update_wrapper(admin_required_wrapper, func)

# get the user
def get_user(request):
  # push the expiration of the session back
  request.session.set_expiry(settings.SESSION_COOKIE_AGE)
  
  # set up CSRF protection if needed
  if not request.session.has_key('csrf_token') or type(request.session['csrf_token']) != str:
    request.session['csrf_token'] = str(uuid.uuid4())

  if request.session.has_key('user'):
    user = request.session['user']

    # find the user
    user_obj = User.get_by_type_and_id(user['type'], user['user_id'])
    return user_obj
  else:
    return None  

def check_csrf(request):
  if request.method != "POST":
    return HttpResponseNotAllowed("only a POST for this URL")
    
  if (not request.POST.has_key('csrf_token')) or (request.POST['csrf_token'] != request.session['csrf_token']):
    raise Exception("A CSRF problem was detected")

def save_in_session_across_logouts(request, field_name, field_value):
  fields_to_save = request.session.get(FIELDS_TO_SAVE, [])
  if field_name not in fields_to_save:
    fields_to_save.append(field_name)
    request.session[FIELDS_TO_SAVE] = fields_to_save

  request.session[field_name] = field_value
