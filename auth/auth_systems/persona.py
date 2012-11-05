"""
Persona + Voter Authentication
"""

from django.core.urlresolvers import reverse
from django import forms
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponseRedirect

import logging, requests

# some parameters to indicate that status updating is possible
STATUS_UPDATES = False
LOGIN_MESSAGE = "Log in with my Email"


def create_user(username, password, name = None):
  from auth.models import User
  
  user = User.get_by_type_and_id('persona', username)
  if user:
    raise Exception('user exists')
  
  info = {'name': name}
  user = User.update_or_create(user_type='persona', user_id=username, info = info)
  user.save()

class PersonaLoginForm(forms.Form):
  assertion = forms.CharField(widget=forms.HiddenInput())

# the view for logging in
def persona_login_view(request):
  from auth.view_utils import render_template
  from auth.views import after
  from auth.models import User

  error = None
  
  if request.method == "GET":
    form = PersonaLoginForm()
  else:
    form = PersonaLoginForm(request.POST)

    # set this in case we came here straight from the multi-login chooser
    # and thus did not have a chance to hit the "start/password" URL
    request.session['auth_system_name'] = 'persona'
    if request.POST.has_key('return_url'):
      request.session['auth_return_url'] = request.POST.get('return_url')

    if form.is_valid():
      assertion = form.cleaned_data['assertion'].strip()

      # go verify the assertion
      payload = {"assertion": assertion, "audience": settings.SECURE_URL_HOST}
      result = requests.post("https://verifier.login.persona.org/verify", data = payload, verify=True).json

      if result['status'] == 'okay':
        email = result['email']
        request.session['persona_user'] = {'email': email , 'info': None, 'name': email}

        # figure out if we have this user
        try:
          user = User.get_by_type_and_id('persona', email)
          if user.info:
            request.session['persona_user'] = {'email': email , 'info': user.info, 'name': email}
            # we got what we need
            return HttpResponseRedirect(reverse(after))
        except User.DoesNotExist:
          # no user, let's keep going we're going to prompt for info
          pass

        return HttpResponseRedirect(reverse(persona_user_info_view))

      # otherwise
      error = 'Bad Assertion'
  
  return render_template(request, 'persona/login', {'form': form, 'error': error})

class PersonaUserInfoForm(forms.Form):
  last_name = forms.CharField(max_length = 80)
  first_names = forms.CharField(max_length = 80, label="First Name(s)")
  zip_code = forms.CharField(max_length = 5)
  street_address = forms.CharField(max_length = 250)

def persona_user_info_view(request):
  from auth.view_utils import render_template
  from auth.views import after

  user = request.session['persona_user']
  if request.method == "GET":
    form = PersonaUserInfoForm()
  else:
    form = PersonaUserInfoForm(request.POST)

    if form.is_valid():
      user['info'] = form.cleaned_data
      request.session['persona_user'] = user
      return HttpResponseRedirect(reverse(after))

  return render_template(request, 'persona/info', {'form': form, 'email': user['email']})
      
def get_auth_url(request, redirect_url = None):
  return reverse(persona_login_view)
    
def get_user_info_after_auth(request):
  user = request.session['persona_user']
  del request.session['persona_user']

  return {'type': 'persona', 'user_id' : user['email'], 'name': user['name'], 'info': user['info'], 'token': None}
    
def update_status(token, message):
  pass
  
def send_message(user_id, user_name, user_info, subject, body):
  email = user_id
  name = user_name or user_info.get('name', email)
  send_mail(subject, body, settings.SERVER_EMAIL, ["%s <%s>" % (name, email)], fail_silently=False)    

def persona_logout_view(request):
  from auth.view_utils import render_template
  from auth.views import after
  current_user = request.session['persona_user_to_logout']
  del request.session['persona_user_to_logout']
  return render_template(request, 'persona/logout', {"current_user": current_user, "return_url": settings.SECURE_URL_HOST + reverse(after)})
  
def do_logout(request, user):
  request.session['persona_user_to_logout'] = user['user_id']
  return HttpResponseRedirect(reverse(persona_logout_view))
  
