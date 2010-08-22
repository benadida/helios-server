"""
Google Authentication

"""

from django.http import *
from django.core.mail import send_mail
from django.conf import settings

import sys, os, cgi, urllib, urllib2, re
from xml.etree import ElementTree

from openid import view_helpers

# some parameters to indicate that status updating is not possible
STATUS_UPDATES = False

# display tweaks
LOGIN_MESSAGE = "Log in with my Google Account"
OPENID_ENDPOINT = 'https://www.google.com/accounts/o8/id'

# FIXME!
# TRUST_ROOT = 'http://localhost:8000'
# RETURN_TO = 'http://localhost:8000/auth/after'

def get_auth_url(request, redirect_url):
  # FIXME?? TRUST_ROOT should be diff than return_url?
  request.session['google_redirect_url'] = redirect_url
  url = view_helpers.start_openid(request.session, OPENID_ENDPOINT, redirect_url, redirect_url)
  return url

def get_user_info_after_auth(request):
  data = view_helpers.finish_openid(request.session, request.GET, request.session['google_redirect_url'])

  return {'type' : 'google', 'user_id': data['ax']['email'][0], 'name': "%s %s" % (data['ax']['firstname'][0], data['ax']['lastname'][0]), 'info': {}, 'token':{}}
    
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
