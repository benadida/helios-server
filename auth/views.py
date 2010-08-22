"""
Views for authentication

Ben Adida
2009-07-05
"""

from django.http import *
from django.core.urlresolvers import reverse

from view_utils import *
from auth.security import get_user

import auth_systems
from auth_systems import AUTH_SYSTEMS
from auth_systems import password
import auth

import copy

from models import User

from security import FIELDS_TO_SAVE

def index(request):
  """
  the page from which one chooses how to log in.
  """
  
  user = get_user(request)

  # single auth system?
  if len(auth.ENABLED_AUTH_SYSTEMS) == 1 and not user:
    return HttpResponseRedirect(reverse(start, args=[auth.ENABLED_AUTH_SYSTEMS[0]])+ '?return_url=' + request.GET.get('return_url', ''))

  #if auth.DEFAULT_AUTH_SYSTEM and not user:
  #  return HttpResponseRedirect(reverse(start, args=[auth.DEFAULT_AUTH_SYSTEM])+ '?return_url=' + request.GET.get('return_url', ''))
  
  default_auth_system_obj = None
  if auth.DEFAULT_AUTH_SYSTEM:
    default_auth_system_obj = auth_systems.AUTH_SYSTEMS[auth.DEFAULT_AUTH_SYSTEM]

  form = password.LoginForm()

  return render_template(request,'index', {'return_url' : request.GET.get('return_url', '/'),
                                           'enabled_auth_systems' : auth.ENABLED_AUTH_SYSTEMS,
                                           'default_auth_system': auth.DEFAULT_AUTH_SYSTEM,
                                           'default_auth_system_obj': default_auth_system_obj,
                                           'form' : form})

def login_box_raw(request, return_url='/', auth_systems = None):
  """
  a chunk of HTML that shows the various login options
  """
  default_auth_system_obj = None
  if auth.DEFAULT_AUTH_SYSTEM:
    default_auth_system_obj = auth_systems.AUTH_SYSTEMS[auth.DEFAULT_AUTH_SYSTEM]
  
  enabled_auth_systems = auth_systems or auth.ENABLED_AUTH_SYSTEMS

  form = password.LoginForm()

  return render_template_raw(request, 'login_box', {
      'enabled_auth_systems': enabled_auth_systems, 'return_url': return_url,
      'default_auth_system': auth.DEFAULT_AUTH_SYSTEM, 'default_auth_system_obj': default_auth_system_obj,
      'form' : form})
  
def do_local_logout(request):
  """
  if there is a logged-in user, it is saved in the new session's "user_for_remote_logout"
  variable.
  """

  user = None

  if request.session.has_key('user'):
    user = request.session['user']
    
  # 2010-08-14 be much more aggressive here
  # we save a few fields across session renewals,
  # but we definitely kill the session and renew
  # the cookie
  field_names_to_save = request.session.get(FIELDS_TO_SAVE, [])
  fields_to_save = dict([(name, request.session.get(name, None)) for name in field_names_to_save])

  # let's not forget to save the list of fields to save
  field_names_to_save.append(FIELDS_TO_SAVE)
  fields_to_save[FIELDS_TO_SAVE] = field_names_to_save

  request.session.flush()

  for name in field_names_to_save:
    request.session[name] = fields_to_save[name]

  request.session['user_for_remote_logout'] = user

def do_remote_logout(request, user, return_url="/"):
  # FIXME: do something with return_url
  auth_system = AUTH_SYSTEMS[user['type']]
  
  # does the auth system have a special logout procedure?
  if hasattr(auth_system, 'do_logout'):
    response = auth_system.do_logout(request.session.get('user_for_remote_logout', None))
    return response

def do_complete_logout(request, return_url="/"):
  do_local_logout(request)
  user_for_remote_logout = request.session.get('user_for_remote_logout', None)
  if user_for_remote_logout:
    response = do_remote_logout(request, user_for_remote_logout, return_url)
    return response
  return None
  
def logout(request):
  """
  logout
  """

  return_url = request.GET.get('return_url',"/")
  response = do_complete_logout(request, return_url)
  if response:
    return response
  
  return HttpResponseRedirect(return_url)
  
def start(request, system_name):
  if not (system_name in auth.ENABLED_AUTH_SYSTEMS):
    return HttpResponseRedirect(reverse(index))
    
  request.session.save()
  
  # store in the session the name of the system used for auth
  request.session['auth_system_name'] = system_name
  
  # where to return to when done
  request.session['auth_return_url'] = request.GET.get('return_url', '/')

  # get the system
  system = AUTH_SYSTEMS[system_name]  
  
  # where to send the user to?
  redirect_url = "%s%s" % (settings.URL_HOST,reverse(after))
  auth_url = system.get_auth_url(request, redirect_url=redirect_url)
  
  if auth_url:
    return HttpResponseRedirect(auth_url)
  else:
    return HttpResponse("an error occurred trying to contact " + system_name +", try again later")

def after(request):
  # which auth system were we using?
  if not request.session.has_key('auth_system_name'):
    do_local_logout(request)
    return HttpResponseRedirect("/")
    
  system = AUTH_SYSTEMS[request.session['auth_system_name']]
  
  # get the user info
  user = system.get_user_info_after_auth(request)

  if user:
    # get the user and store any new data about him
    user_obj = User.update_or_create(user['type'], user['user_id'], user['name'], user['info'], user['token'])
    
    request.session['user'] = user
  else:
    # we were logging out
    pass

  # does the auth system want to present an additional view?
  # this is, for example, to prompt the user to follow @heliosvoting
  # so they can hear about election results
  if hasattr(system, 'user_needs_intervention'):
    intervention_response = system.user_needs_intervention(user['user_id'], user['info'], user['token'])
    if intervention_response:
      return intervention_response

  # go to the after intervention page. This is for modularity
  return HttpResponseRedirect(reverse(after_intervention))

def after_intervention(request):
  return HttpResponseRedirect(request.session['auth_return_url'] or "/")

