"""
Utilities.

Ben Adida - ben@adida.net
2005-04-11
"""

import urllib, re, sys, datetime, urlparse, string
import threading

# utils from auth, too
from auth.utils import *

from django.conf import settings
  
import random, logging
import sha, hmac, base64

def do_hmac(k,s):
  """
  HMAC a value with a key, hex output
  """
  mac = hmac.new(k, s, sha)
  return mac.hexdigest()


def split_by_length(str, length, rejoin_with=None):
  """
  split a string by a given length
  """
  str_arr = []
  counter = 0
  while counter<len(str):
    str_arr.append(str[counter:counter+length])
    counter += length

  if rejoin_with:
    return rejoin_with.join(str_arr)
  else:
    return str_arr
    

def urlencode(str):
    """
    URL encode
    """
    if not str:
        return ""

    return urllib.quote(str)

def urlencodeall(str):
    """
    URL encode everything even unresreved chars
    """
    if not str:
        return ""

    return string.join(['%' + s.encode('hex') for s in str], '')

def urldecode(str):
    if not str:
        return ""

    return urllib.unquote(str)

def dictToURLParams(d):
  if d:
    return '&'.join([i + '=' + urlencode(v) for i,v in d.items()])
  else:
    return None
##
## XML escaping and unescaping
## 

def xml_escape(s):
    raise Exception('not implemented yet')

def xml_unescape(s):
    new_s = s.replace('&lt;','<').replace('&gt;','>')
    return new_s
    
##
## XSS attack prevention
##

def xss_strip_all_tags(s):
    """
    Strips out all HTML.
    """
    return s
    def fixup(m):
        text = m.group(0)
        if text[:1] == "<":
            return "" # ignore tags
        if text[:2] == "&#":
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        elif text[:1] == "&":
            import htmlentitydefs
            entity = htmlentitydefs.entitydefs.get(text[1:-1])
            if entity:
                if entity[:2] == "&#":
                    try:
                        return unichr(int(entity[2:-1]))
                    except ValueError:
                        pass
                else:
                    return unicode(entity, "iso-8859-1")
        return text # leave as is
        
    return re.sub("(?s)<[^>]*>|&#?\w+;", fixup, s)
    
 
random.seed()

def random_string(length=20):
    random.seed()
    ALPHABET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    r_string = ''
    for i in range(length):
        r_string += random.choice(ALPHABET)

    return r_string

def get_host():
  return settings.SERVER_HOST
  
def get_prefix():
  return settings.SERVER_PREFIX
  

##
## Datetime utilities
##

def string_to_datetime(str, fmt="%Y-%m-%d %H:%M"):
  if str == None:
    return None

  return datetime.datetime.strptime(str, fmt)
  
##
## email
##

from django.core import mail as django_mail

def send_email(sender, recpt_lst, subject, body):
  # subject up until the first newline
  subject = subject.split("\n")[0]
  django_mail.send_mail(subject, body, sender, recpt_lst, fail_silently=True)
  

  
