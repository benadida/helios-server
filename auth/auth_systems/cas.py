"""
CAS (Princeton) Authentication

Some code borrowed from
https://sp.princeton.edu/oit/sdp/CAS/Wiki%20Pages/Python.aspx
"""

from django.http import *
from django.core.mail import send_mail
from django.conf import settings

import sys, os, cgi, urllib, urllib2, re
from xml.etree import ElementTree

CAS_EMAIL_DOMAIN = "princeton.edu"
CAS_URL= 'https://fed.princeton.edu/cas/'
CAS_LOGOUT_URL = 'https://fed.princeton.edu/cas/logout?service=%s'

# eligibility checking
if hasattr(settings, 'CAS_USERNAME'):
  CAS_USERNAME = settings.CAS_USERNAME
  CAS_PASSWORD = settings.CAS_PASSWORD
  CAS_ELIGIBILITY_URL = settings.CAS_ELIGIBILITY_URL
  CAS_ELIGIBILITY_REALM = settings.CAS_ELIGIBILITY_REALM

# display tweaks
LOGIN_MESSAGE = "Log in with my NetID"

def _get_service_url():
  # FIXME current URL
  from auth.views import after
  from django.conf import settings
  from django.core.urlresolvers import reverse
  
  return settings.URL_HOST + reverse(after)
  
def get_auth_url(request):
  return CAS_URL + 'login?service=' + urllib.quote(_get_service_url())

def get_user_category(user_id):
  theurl = CAS_ELIGIBILITY_URL % user_id

  auth_handler = urllib2.HTTPBasicAuthHandler()
  auth_handler.add_password(realm=CAS_ELIGIBILITY_REALM, uri= theurl, user= CAS_USERNAME, passwd = CAS_PASSWORD)
  opener = urllib2.build_opener(auth_handler)
  urllib2.install_opener(opener)
  
  result = urllib2.urlopen(CAS_ELIGIBILITY_URL % user_id).read().strip()
  parsed_result = ElementTree.fromstring(result)
  return parsed_result.text
  
  
def get_user_info(user_id):
  url = 'http://dsml.princeton.edu/'
  headers = {'SOAPAction': "#searchRequest", 'Content-Type': 'text/xml'}
  
  request_body = """<?xml version='1.0' encoding='UTF-8'?> 
  <soap-env:Envelope 
     xmlns:xsd='http://www.w3.org/2001/XMLSchema'
     xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'
     xmlns:soap-env='http://schemas.xmlsoap.org/soap/envelope/'> 
     <soap-env:Body> 
        <batchRequest xmlns='urn:oasis:names:tc:DSML:2:0:core'
  requestID='searching'>
        <searchRequest 
           dn='o=Princeton University, c=US'
           scope='wholeSubtree'
           derefAliases='neverDerefAliases'
           sizeLimit='200'> 
              <filter>
                   <equalityMatch name='uid'>
                            <value>%s</value>
                    </equalityMatch>
               </filter>
               <attributes>
                       <attribute name="displayName"/>
                       <attribute name="pustatus"/>
               </attributes>
        </searchRequest>
       </batchRequest>
     </soap-env:Body> 
  </soap-env:Envelope>
""" % user_id

  req = urllib2.Request(url, request_body, headers)
  response = urllib2.urlopen(req).read()
  
  # parse the result
  from xml.dom.minidom import parseString
  
  response_doc = parseString(response)
  
  # get the value elements (a bit of a hack but no big deal)
  values = response_doc.getElementsByTagName('value')
  
  return {'name' : values[0].firstChild.wholeText, 'category' : values[1].firstChild.wholeText}
  
def get_user_info_after_auth(request):
  ticket = request.GET.get('ticket', None)
  
  # if no ticket, this is a logout
  if not ticket:
    return None

  # fetch the information from the CAS server
  val_url = CAS_URL + "validate" + \
     '?service=' + urllib.quote(_get_service_url()) + \
     '&ticket=' + urllib.quote(ticket)
  r = urllib.urlopen(val_url).readlines()   # returns 2 lines

  # success
  if len(r) == 2 and re.match("yes", r[0]) != None:
    netid = r[1].strip()
    
    category = get_user_category(netid)
    info = {'name': netid, 'category': category}
      
    return {'type': 'cas', 'user_id': netid, 'name': netid, 'info': info, 'token': None}
  else:
    return None
    
def do_logout(user):
  """
  Perform logout of CAS by redirecting to the CAS logout URL
  """
  return HttpResponseRedirect(CAS_LOGOUT_URL % _get_service_url())
  
def update_status(token, message):
  """
  simple update
  """
  pass

def send_message(user_id, name, user_info, subject, body):
  """
  send email, for now just to Princeton
  """
  # if the user_id contains an @ sign already
  if "@" in user_id:
    email = user_id
  else:
    email = "%s@%s" % (user_id, CAS_EMAIL_DOMAIN)
    
  if user_info.has_key('name'):
    name = user_info["name"]
  else:
    name = email
    
  send_mail(subject, body, settings.SERVER_EMAIL, ["%s <%s>" % (name, email)], fail_silently=False)
  
def check_constraint(constraint, user_info):
  if not user_info.has_key('category'):
    return False
  return constraint['year'] == user_info['category']
