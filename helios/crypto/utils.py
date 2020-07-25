"""
Crypto Utils
"""
import hashlib
import hmac, base64, json

from hashlib import sha256
  
def hash_b64(s):
  """
  hash the string using sha1 and produce a base64 output
  removes the trailing "="
  """
  hasher = sha256(s)
  result= base64.b64encode(hasher.digest())[:-1]
  return result

def to_json(d, no_whitespace=False):
  if no_whitespace:
    return json.dumps(d, sort_keys=True, separators=(',',':'))
  else:
    return json.dumps(d, sort_keys=True)

def from_json(json_str):
  if not json_str: return None
  return json.loads(json_str)


def do_hmac(k,s):
  """
  HMAC a value with a key, hex output
  """
  mac = hmac.new(k, s, hashlib.sha1)
  return mac.hexdigest()