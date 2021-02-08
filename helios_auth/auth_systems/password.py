"""
Username/Password Authentication
"""

from django.urls import reverse
from django import forms
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponseRedirect
from django.conf.urls import url

from helios_auth import url_names

import logging

# some parameters to indicate that status updating is possible
STATUS_UPDATES = False
PASSWORD_LOGIN_URL_NAME = "auth@password@login"
PASSWORD_FORGOTTEN_URL_NAME = "auth@password@forgotten"

def create_user(username, password, name = None):
  from helios_auth.models import User
  
  user = User.get_by_type_and_id('password', username)
  if user:
    raise Exception('user exists')
  
  info = {'password' : password, 'name': name}
  user = User.update_or_create(user_type='password', user_id=username, info = info)
  user.save()

class LoginForm(forms.Form):
  username = forms.CharField(max_length=50)
  password = forms.CharField(widget=forms.PasswordInput(), max_length=100)

def password_check(user, password):
  return (user and user.info['password'] == password)
  
# the view for logging in
def password_login_view(request):
  from helios_auth.view_utils import render_template
  from helios_auth.views import after
  from helios_auth.models import User

  error = None
  
  if request.method == "GET":
    form = LoginForm()
  else:
    form = LoginForm(request.POST)

    # set this in case we came here straight from the multi-login chooser
    # and thus did not have a chance to hit the "start/password" URL
    request.session['auth_system_name'] = 'password'
    if 'return_url' in request.POST:
      request.session['auth_return_url'] = request.POST.get('return_url')

    if form.is_valid():
      username = form.cleaned_data['username'].strip()
      password = form.cleaned_data['password'].strip()
      try:
        user = User.get_by_type_and_id('password', username)
        if password_check(user, password):
          request.session['password_user_id'] = user.user_id
          return HttpResponseRedirect(reverse(url_names.AUTH_AFTER))
      except User.DoesNotExist:
        pass
      error = 'Bad Username or Password'
  
  return render_template(request, 'password/login', {'form': form, 'error': error})
    
def password_forgotten_view(request):
  """
  forgotten password view and submit.
  includes return_url
  """
  from helios_auth.view_utils import render_template
  from helios_auth.models import User

  if request.method == "GET":
    return render_template(request, 'password/forgot', {'return_url': request.GET.get('return_url', '')})
  else:
    username = request.POST['username']
    return_url = request.POST['return_url']
    
    try:
      user = User.get_by_type_and_id('password', username)
    except User.DoesNotExist:
      return render_template(request, 'password/forgot', {'return_url': request.GET.get('return_url', ''), 'error': 'no such username'})
    
    body = """

This is a password reminder:

Your username: %s
Your password: %s

--
%s
""" % (user.user_id, user.info['password'], settings.SITE_TITLE)

    # FIXME: make this a task
    send_mail('password reminder', body, settings.SERVER_EMAIL, ["%s <%s>" % (user.info['name'], user.info['email'])], fail_silently=False)
    
    return HttpResponseRedirect(return_url)
  
def get_auth_url(request, redirect_url = None):
  return reverse(PASSWORD_LOGIN_URL_NAME)
    
def get_user_info_after_auth(request):
  from helios_auth.models import User
  user = User.get_by_type_and_id('password', request.session['password_user_id'])
  del request.session['password_user_id']
  
  return {'type': 'password', 'user_id' : user.user_id, 'name': user.name, 'info': user.info, 'token': None}
    
def update_status(token, message):
  pass
  
def send_message(user_id, user_name, user_info, subject, body):
  email = user_id
  name = user_name or user_info.get('name', email)
  send_mail(subject, body, settings.SERVER_EMAIL, ["\"%s\" <%s>" % (name, email)], fail_silently=False)    


#
# Election Creation
#

def can_create_election(user_id, user_info):
  return True


urlpatterns = [
  url(r'^password/login', password_login_view, name=PASSWORD_LOGIN_URL_NAME),
  url(r'^password/forgot', password_forgotten_view, name=PASSWORD_FORGOTTEN_URL_NAME)
]
