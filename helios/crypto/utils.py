"""
Crypto Utils
"""

import hmac, base64

from django.utils import simplejson

from hashlib import sha256
  
def hash_b64(s):
  """
  hash the string using sha1 and produce a base64 output
  removes the trailing "="
  """
  hasher = sha256(s)
  result= base64.b64encode(hasher.digest())[:-1]
  return result

def to_json(d):
  return simplejson.dumps(d, sort_keys=True)

def from_json(json_str):
  if not json_str: return None
  return simplejson.loads(json_str)

def hash_vote(vote):
  """
  hash a canonical representation of a vote in dict format
  """
  stringification = "//".join([
      "|".join([ "%s,%s" % (c["alpha"], c["beta"]) for c in a["choices"] ])
      + "#" +
      "|".join([
          "/".join([ "%s,%s,%s,%s"
                     % (pi["commitment"]["A"], pi["commitment"]["B"], pi["challenge"], pi["response"])
                     for pi in p ])
          for p in a["individual_proofs"] ])
      + "#" +
      "/".join([ "%s,%s,%s,%s"
                 % (pi["commitment"]["A"], pi["commitment"]["B"], pi["challenge"], pi["response"])
                 for pi in a["overall_proof"] ])
      for a in vote["answers"] ]) + "#" + vote["election_hash"] + "#" + vote["election_uuid"]
  return hash_b64(stringification)
