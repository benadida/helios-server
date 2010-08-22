"""
Username/Password Authentication
"""

from django.core.urlresolvers import reverse
from django import forms
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponseRedirect

import logging

# some parameters to indicate that status updating is possible
STATUS_UPDATES = False


def create_user(username, password, name = None):
  from auth.models import User
  
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
  from auth.view_utils import render_template
  from auth.views import after
  from auth.models import User

  error = None
  
  if request.method == "GET":
    form = LoginForm()
  else:
    form = LoginForm(request.POST)

    if form.is_valid():
      username = form.cleaned_data['username'].strip()
      password = form.cleaned_data['password'].strip()
      try:
        user = User.get_by_type_and_id('password', username)
        if password_check(user, password):
          # set this in case we came here from another location than 
          # the normal login process
          request.session['auth_system_name'] = 'password'
          if request.POST.has_key('return_url'):
            request.session['auth_return_url'] = request.POST.get('return_url')

          request.session['user'] = user
          return HttpResponseRedirect(reverse(after))
      except User.DoesNotExist:
        pass
      error = 'Bad Username or Password'
  
  return render_template(request, 'password/login', {'form': form, 'error': error})
    
def password_forgotten_view(request):
  """
  forgotten password view and submit.
  includes return_url
  """
  from auth.view_utils import render_template
  from auth.models import User

  if request.method == "GET":
    return render_template(request, 'password/forgot', {'return_url': request.GET.get('return_url', '')})
  else:
    username = request.POST['username']
    return_url = request.POST['return_url']
    
    user = User.get_by_type_and_id('password', username)
    
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
  return reverse(password_login_view)
    
def get_user_info_after_auth(request):
  user = request.session['user']
  user_info = user.info
  
  return {'type': 'password', 'user_id' : user.user_id, 'name': user.name, 'info': user.info, 'token': None}
    
def update_status(token, message):
  pass
  
def send_message(user_id, user_name, user_info, subject, body):
  if user_info.has_key('email'):
    email = user_info['email']
    name = user_info.get('name', email)
    send_mail(subject, body, settings.SERVER_EMAIL, ["%s <%s>" % (name, email)], fail_silently=False)    
