"""
Utilities.

Ben Adida - ben@adida.net
2005-04-11
"""

import urllib.request, urllib.parse, urllib.error, re, datetime, string

# utils from helios_auth, too
from helios_auth.utils import *

from django.conf import settings
  
import random, logging


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

    return urllib.parse.quote(str)

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

    return urllib.parse.unquote(str)

def dictToURLParams(d):
  if d:
    return '&'.join([i + '=' + urlencode(v) for i,v in list(d.items())])
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
                    return chr(int(text[3:-1], 16))
                else:
                    return chr(int(text[2:-1]))
            except ValueError:
                pass
        elif text[:1] == "&":
            import html.entities
            entity = html.entities.entitydefs.get(text[1:-1])
            if entity:
                if entity[:2] == "&#":
                    try:
                        return chr(int(entity[2:-1]))
                    except ValueError:
                        pass
                else:
                    return str(entity, "iso-8859-1")
        return text # leave as is
        
    return re.sub("(?s)<[^>]*>|&#?\w+;", fixup, s)
    
 
random.seed()

def random_string(length=20, alphabet=None):
    random.seed()
    ALPHABET = alphabet or 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
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

  
##
## raw SQL and locking
##

def one_val_raw_sql(raw_sql, values=[]):
  """
  for a simple aggregate
  """
  from django.db import connection
  cursor = connection.cursor()

  cursor.execute(raw_sql, values)
  return cursor.fetchone()[0]

def lock_row(model, pk):
  """
  you almost certainly want to use lock_row inside a commit_on_success function
  Eventually, in Django 1.2, this should move to the .for_update() support
  """

  from django.db import connection, transaction
  cursor = connection.cursor()

  cursor.execute("select * from " + model._meta.db_table + " where id = %s for update", [pk])
  row = cursor.fetchone()

  # if this is under transaction management control, mark the transaction dirty
  try:
    transaction.set_dirty()
  except:
    pass

  return row
