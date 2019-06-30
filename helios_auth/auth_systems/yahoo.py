"""
Yahoo Authentication

"""

from django.conf import settings
from django.core.mail import send_mail

from .openid import view_helpers

# some parameters to indicate that status updating is not possible
STATUS_UPDATES = False

# display tweaks
LOGIN_MESSAGE = "Log in with my Yahoo Account"
OPENID_ENDPOINT = 'yahoo.com'

def get_auth_url(request, redirect_url):
  request.session['yahoo_redirect_url'] = redirect_url
  url = view_helpers.start_openid(request.session, OPENID_ENDPOINT, redirect_url, redirect_url)
  return url

def get_user_info_after_auth(request):
  data = view_helpers.finish_openid(request.session, request.GET, request.session['yahoo_redirect_url'])

  return {'type' : 'yahoo', 'user_id': data['ax']['email'][0], 'name': data['ax']['fullname'][0], 'info': {'email': data['ax']['email'][0]}, 'token':{}}
    
def do_logout(user):
  """
  logout of Yahoo
  """
  return None
  
def update_status(token, message):
  """
  simple update
  """
  pass

def send_message(user_id, user_name, user_info, subject, body):
  """
  send email to yahoo user, user_id is email for yahoo and other openID logins.
  """
  send_mail(subject, body, settings.SERVER_EMAIL, ["%s <%s>" % (user_name, user_id)], fail_silently=False)
  
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
