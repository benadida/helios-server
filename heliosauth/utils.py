"""
Some basic utils
(previously were in helios module, but making things less interdependent

2010-08-17
"""

from django.utils import simplejson

def force_utf8(s):
  if isinstance(s, unicode):
    return s.encode('utf8')
  else:
    return s

## JSON
def to_json(d):
  return simplejson.dumps(d, sort_keys=True)

def from_json(json_str):
  if not json_str: return None
  return simplejson.loads(json_str)

def JSONtoDict(json):
    x=simplejson.loads(json)
    return x

def JSONFiletoDict(filename):
  f = open(filename, 'r')
  content = f.read()
  f.close()
  return JSONtoDict(content)



