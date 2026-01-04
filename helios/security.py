"""
Helios Security -- mostly access control

Ben Adida (ben@adida.net)
"""

import urllib.parse
# nicely update the wrapper function
from functools import update_wrapper

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.http import HttpResponseRedirect
from django.urls import reverse

import helios
from helios_auth.security import get_user
from .models import Voter, Trustee, Election


class HSTSMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        if settings.STS:
          response['Strict-Transport-Security'] = "max-age=31536000; includeSubDomains; preload"
        return response


class ContentSecurityPolicyMiddleware:
    """
    Middleware to add Content-Security-Policy header to responses.

    The CSP is designed to be restrictive while allowing the necessary
    functionality for Helios voting system:

    - Scripts: 'self' with 'unsafe-inline' and 'unsafe-eval' required due to
      legacy inline scripts, onclick handlers, and jQuery JSON eval usage
    - Styles: 'self' with 'unsafe-inline' for inline style attributes
    - Images: 'self' and data: URIs (used in key generation download links)
    - Workers: 'self' and blob: for Web Workers used in ballot encryption
    - Forms: restricted to 'self' to prevent form hijacking
    - Frame ancestors: 'self' to prevent clickjacking (supplements X-Frame-Options)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if not getattr(settings, 'CSP_ENABLED', True):
            return response

        # Build CSP directives
        directives = []

        # Default policy - restrict everything to same origin by default
        directives.append("default-src 'self'")

        # Script sources
        # 'unsafe-inline' required for: inline <script> tags, onclick handlers
        # 'unsafe-eval' required for: jQuery.parseJSON using eval(), jTemplates
        script_src = ["'self'", "'unsafe-inline'", "'unsafe-eval'"]
        extra_script_src = getattr(settings, 'CSP_SCRIPT_SRC_EXTRA', [])
        script_src.extend(extra_script_src)
        directives.append("script-src " + " ".join(script_src))

        # Style sources
        # 'unsafe-inline' required for: inline style attributes
        style_src = ["'self'", "'unsafe-inline'"]
        extra_style_src = getattr(settings, 'CSP_STYLE_SRC_EXTRA', [])
        style_src.extend(extra_style_src)
        directives.append("style-src " + " ".join(style_src))

        # Image sources
        # data: required for: download links using data: URIs in key generation
        img_src = ["'self'", "data:"]
        extra_img_src = getattr(settings, 'CSP_IMG_SRC_EXTRA', [])
        img_src.extend(extra_img_src)
        directives.append("img-src " + " ".join(img_src))

        # Font sources
        directives.append("font-src 'self'")

        # Connect sources (XHR, fetch, WebSocket)
        connect_src = ["'self'"]
        extra_connect_src = getattr(settings, 'CSP_CONNECT_SRC_EXTRA', [])
        connect_src.extend(extra_connect_src)
        directives.append("connect-src " + " ".join(connect_src))

        # Worker sources (Web Workers for encryption)
        # blob: may be needed for some worker implementations
        directives.append("worker-src 'self' blob:")

        # Form action - restrict form submissions to same origin
        directives.append("form-action 'self'")

        # Frame ancestors - prevent embedding in frames (clickjacking protection)
        # This supplements X-Frame-Options
        frame_ancestors = getattr(settings, 'CSP_FRAME_ANCESTORS', "'self'")
        directives.append(f"frame-ancestors {frame_ancestors}")

        # Base URI - prevent base tag hijacking
        directives.append("base-uri 'self'")

        # Object/embed sources - disable plugins
        directives.append("object-src 'none'")

        # Build the policy string
        policy = "; ".join(directives)

        # Use report-only mode if configured (useful for testing)
        if getattr(settings, 'CSP_REPORT_ONLY', False):
            header_name = 'Content-Security-Policy-Report-Only'
        else:
            header_name = 'Content-Security-Policy'

        # Add report URI if configured
        report_uri = getattr(settings, 'CSP_REPORT_URI', None)
        if report_uri:
            policy += f"; report-uri {report_uri}"

        response[header_name] = policy

        return response

# current voter
def get_voter(request, user, election):
  """
  return the current voter
  """
  voter = None
  if 'CURRENT_VOTER_ID' in request.session:
    voter = Voter.objects.get(id=request.session['CURRENT_VOTER_ID'])
    if voter.election != election:
      voter = None

  if not voter:
    if user:
      voter = Voter.get_by_election_and_user(election, user)
  
  return voter

# a function to check if the current user is a trustee
HELIOS_TRUSTEE_UUID = 'helios_trustee_uuid'
def get_logged_in_trustee(request):
  if HELIOS_TRUSTEE_UUID in request.session:
    return Trustee.get_by_uuid(request.session[HELIOS_TRUSTEE_UUID])
  else:
    return None

def set_logged_in_trustee(request, trustee):
  request.session[HELIOS_TRUSTEE_UUID] = trustee.uuid

#
# some common election checks
#
def do_election_checks(election, props):
  # frozen
  if 'frozen' in props:
    frozen = props['frozen']
  else:
    frozen = None
  
  # newvoters (open for registration)
  if 'newvoters' in props:
    newvoters = props['newvoters']
  else:
    newvoters = None
  
  # frozen check
  if frozen is not None:
    if frozen and not election.frozen_at:
      raise PermissionDenied()
    if not frozen and election.frozen_at:
      raise PermissionDenied()
    
  # open for new voters check
  if newvoters is not None:
    if election.can_add_voters() != newvoters:
      raise PermissionDenied()

  
def get_election_by_uuid(uuid):
  if not uuid:
    raise Exception("no election ID")
      
  return Election.get_by_uuid(uuid)
  
# decorator for views that pertain to an election
# takes parameters:
# frozen - is the election frozen
# newvoters - does the election accept new voters
def election_view(**checks):
  
  def election_view_decorator(func):
    def election_view_wrapper(request, election_uuid=None, *args, **kw):
      election = get_election_by_uuid(election_uuid)

      if not election:
        raise Http404

      # do checks
      do_election_checks(election, checks)

      # if private election, only logged in voters
      if election.private_p and not checks.get('allow_logins',False):
        from .views import password_voter_login
        if not user_can_see_election(request, election):
          return_url = request.get_full_path()
          return HttpResponseRedirect("%s?%s" % (reverse(password_voter_login, args=[election.uuid]), urllib.parse.urlencode({
                  'return_url' : return_url
                  })))
    
      return func(request, election, *args, **kw)

    return update_wrapper(election_view_wrapper, func)
    
  return election_view_decorator

def user_can_admin_election(user, election):
  if not user:
    return False

  # site administrator, election creator, or listed administrator
  return user.admin_p or election.admin == user or election.admins.filter(pk=user.pk).exists()
  
def user_can_see_election(request, election):
  user = get_user(request)

  if not election.private_p:
    return True

  # election is private
  
  # but maybe this user is the administrator?
  if user_can_admin_election(user, election):
    return True

  # or maybe this is a trustee of the election?
  trustee = get_logged_in_trustee(request)
  if trustee and trustee.election.uuid == election.uuid:
    return True

  # then this user has to be a voter
  return get_voter(request, user, election) is not None


def api_client_can_admin_election(api_client, election):
  return election.api_client == api_client and api_client is not None


# decorator for checking election admin access, and some properties of the election
# frozen - is the election frozen
# newvoters - does the election accept new voters
def election_admin(**checks):
  
  def election_admin_decorator(func):
    def election_admin_wrapper(request, election_uuid=None, *args, **kw):
      election = get_election_by_uuid(election_uuid)

      user = get_user(request)
      if not user_can_admin_election(user, election):
        raise PermissionDenied()
        
      # do checks
      do_election_checks(election, checks)
        
      return func(request, election, *args, **kw)

    return update_wrapper(election_admin_wrapper, func)
    
  return election_admin_decorator
  
def trustee_check(func):
  def trustee_check_wrapper(request, election_uuid, trustee_uuid, *args, **kwargs):
    election = get_election_by_uuid(election_uuid)
    
    trustee = Trustee.get_by_election_and_uuid(election, trustee_uuid)
    
    if trustee == get_logged_in_trustee(request):
      return func(request, election, trustee, *args, **kwargs)
    else:
      raise PermissionDenied()
  
  return update_wrapper(trustee_check_wrapper, func)

def can_create_election(request):
  user = get_user(request)
  if not user:
    return False
    
  if helios.ADMIN_ONLY:
    return user.admin_p
  else:
    return user.can_create_election()
  
def user_can_feature_election(user, election):
  if not user:
    return False
    
  return user.admin_p
  
