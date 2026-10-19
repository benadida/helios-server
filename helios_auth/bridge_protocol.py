"""ALU request authentication. No credentials or identity in browser requests."""
import base64
import hashlib
import hmac
import json
import re
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def digest(value):
  return hashlib.sha256(value.encode('utf-8')).hexdigest()


def challenge(verifier):
  return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode('ascii')).digest()).decode().rstrip('=')


def https_origin(value):
  parsed = urlsplit(value)
  if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or
      parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/')):
    raise ImproperlyConfigured('Bridge origins must be exact HTTPS origins.')
  return value.rstrip('/')


def sign_request(payload):
  encoded = base64.urlsafe_b64encode(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).decode().rstrip('=')
  signature = hmac.new(settings.ALU_BRIDGE_SECRET.encode(),
                       ('alu-bridge-request-v1.' + encoded).encode(), hashlib.sha256).hexdigest()
  return encoded + '.' + signature


def eligible_identity(identity):
  if not isinstance(identity, dict):
    return False
  email = identity.get('email')
  return (identity.get('email_verified') is True and isinstance(email, str) and
          re.fullmatch(r'[^\s@]+@alustudent\.com', email, re.IGNORECASE) is not None and
          isinstance(identity.get('subject'), str) and 0 < len(identity['subject']) <= 100)
