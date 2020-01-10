"""
Clever Authentication

"""

from django.http import *
from django.core.mail import send_mail
from django.conf import settings

import httplib2,json,base64

import sys, os, cgi, urllib, urllib2, re

from oauth2client.client import OAuth2WebServerFlow, OAuth2Credentials

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
    #token_uri="https://clever.com/oauth/tokens",
    token_uri="http://requestb.in/1b18gwf1",
    redirect_uri=redirect_url)
  
def get_auth_url(request, redirect_url):
  flow = get_flow(redirect_url)

  request.session['clever-redirect-url'] = redirect_url
  return flow.step1_get_authorize_url()

def get_user_info_after_auth(request):
  redirect_uri = request.session['clever-redirect-url']
  del request.session['clever-redirect-url']
  flow = get_flow(redirect_uri)

  code = request.GET['code']

  # do the POST manually, because OAuth2WebFlow can't do auth header for token exchange
  http = httplib2.Http(".cache")
  auth_header = "Basic %s" % base64.b64encode(settings.CLEVER_CLIENT_ID + ":" + settings.CLEVER_CLIENT_SECRET)
  resp_headers, content = http.request("https://clever.com/oauth/tokens", "POST", urllib.urlencode({
        "code" : code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
      }), headers = {
        'Authorization': auth_header,
        'Content-Type': "application/x-www-form-urlencoded"
      })

  token_response = json.loads(content)
  access_token = token_response['access_token']

  # package the credentials
  credentials = OAuth2Credentials(access_token, settings.CLEVER_CLIENT_ID, settings.CLEVER_CLIENT_SECRET, None, None, None, None)
  
  # get the nice name
  http = credentials.authorize(http)
  (resp_headers, content) = http.request("https://api.clever.com/me", "GET")

  # {"type":"student","data":{"id":"563395179f7408755c0006b7","district":"5633941748c07c0100000aac","type":"student","created":"2015-10-30T16:04:39.262Z","credentials":{"district_password":"eel7Thohd","district_username":"dianes10"},"dob":"1998-11-01T00:00:00.000Z","ell_status":"Y","email":"diane.s@example.org","gender":"F","grade":"9","hispanic_ethnicity":"Y","last_modified":"2015-10-30T16:04:39.274Z","location":{"zip":"11433"},"name":{"first":"Diane","last":"Schmeler","middle":"J"},"race":"Asian","school":"5633950c62fc41c041000005","sis_id":"738733110","state_id":"114327752","student_number":"738733110"},"links":[{"rel":"self","uri":"/me"},{"rel":"canonical","uri":"/v1.1/students/563395179f7408755c0006b7"},{"rel":"district","uri":"/v1.1/districts/5633941748c07c0100000aac"}]}
  response = json.loads(content)
  
  user_id = response['data']['id']
  user_name = "%s %s" % (response['data']['name']['first'], response['data']['name']['last'])
  user_type = response['type']
  user_district = response['data']['district']
  user_grade = response['data'].get('grade', None)

  print content
  
  # watch out, response also contains email addresses, but not sure whether thsoe are verified or not
  # so for email address we will only look at the id_token
  
  return {'type' : 'clever', 'user_id': user_id, 'name': user_name , 'info': {"district": user_district, "type": user_type, "grade": user_grade}, 'token': {'access_token': access_token}}
    
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

#
# eligibility
#

def check_constraint(constraint, user):
  if not user.info.has_key('grade'):
    return False
  return constraint['grade'] == user.info['grade']

def generate_constraint(category, user):
  """
  generate the proper basic data structure to express a constraint
  based on the category string
  """
  return {'grade': category}

def list_categories(user):
  return [{"id": str(g), "name": "Grade %d" % g} for g in range(3,13)]
  
def eligibility_category_id(constraint):
  return constraint['grade']

def pretty_eligibility(constraint):
  return "Grade %s" % constraint['grade']
  


#
# Election Creation
#

def can_create_election(user_id, user_info):
  """
  Teachers only for now
  """
  return user_info['type'] == 'teacher'
