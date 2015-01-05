# -*- coding: utf-8 -*-

"""
Username/Password Authentication
"""

import httplib
import urllib
import json

from email.Utils import formataddr

from django.core.urlresolvers import reverse
from django import forms
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_str, smart_unicode
from django.contrib.auth.hashers import check_password, make_password

from heliosauth.utils import force_utf8

import logging

# some parameters to indicate that status updating is possible
STATUS_UPDATES = False


def create_user(username, password, name = None, extra_info={}):
  from heliosauth.models import User

  try:
    user = User.get_by_type_and_id('password', username)
  except User.DoesNotExist:
    user = None

  if user:
    raise Exception('user exists')

  info = {'password' : make_password(password), 'name': name}
  info.update(extra_info)
  user = User.update_or_create(user_type='password', user_id=username, info=info)
  user.save()
  return user

class LoginForm(forms.Form):
  username = forms.CharField(label=_('Username'), max_length=50)
  password = forms.CharField(label=_('Password'), widget=forms.PasswordInput(), max_length=100)

def check_ecounting_credentials(username, password):
  url = getattr(settings, 'ECOUNTING_LOGIN_URL', False)
  if not url:
    return False, {}
  username, password = map(force_utf8, [username, password])
  params = urllib.urlencode({'username': username, 'password': password})
  response = urllib.urlopen(url, params)
  data = {}

  try:
    data = json.loads(response.read())
  except:
    return False, data

  if 'success' in data and data['success'] == 'true' and data['message'] == 'Ok':
    if not data['institutionName'] or not data['institutionId']:
      return False, data
    return True, data

  return False, data

def get_institution(user_data):
  from zeus.models import Institution
  try:
    inst = Institution.objects.get(ecounting_id=user_data['institutionId'])
    inst.name = user_data['institutionName']
    inst.save()
  except Institution.DoesNotExist:
    inst = Institution()
    inst.ecounting_id = user_data['institutionId']
    inst.name = user_data['institutionName']
    inst.save()
  return inst

def get_ecounting_user(username, password):
  from heliosauth.models import User

  is_valid, user_data = check_ecounting_credentials(username, password)
  user = None
  if not is_valid:
    return user

  try:
    user = User.get_by_type_and_id('password', username)
    user.institution = get_institution(user_data)
    user.info['name'] = username
    user.info['password'] = make_password(password)
    user.ecounting_account = True
    user.save()
  except User.DoesNotExist:
    if is_valid:
      user = create_user(username, password)
      user.admin_p = True
      user.info['name'] = user.user_id
      user.info['password'] = make_password(password)
      user.ecounting_account = True
      user.institution = get_institution(user_data)
      user.save()

  return user

# the view for logging in
def password_login_view(request):
  from heliosauth.view_utils import render_template
  from heliosauth.views import after
  from heliosauth.models import User

  error = None

  if request.method == "GET":
    form = LoginForm()
  else:
    form = LoginForm(request.POST)

    # set this in case we came here straight from the multi-login chooser
    # and thus did not have a chance to hit the "start/password" URL
    request.session['auth_system_name'] = 'password'
    if request.POST.has_key('return_url'):
      request.session['auth_return_url'] = request.POST.get('return_url')

    if form.is_valid():
      username = form.cleaned_data['username'].strip()
      password = form.cleaned_data['password'].strip()
      try:
        try:
            ecount_user = User.objects.get(user_id=username, ecounting_account=True)
            user = get_ecounting_user(username, password)
        except User.DoesNotExist:
            try:
                user = User.objects.get(user_id=username, ecounting_account=False)
            except User.DoesNotExist:
                user = get_ecounting_user(username, password)
                if not user:
                    raise User.DoesNotExist

        if password_check(user, password):
            request.session['password_user'] = user
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
  from heliosauth.view_utils import render_template
  from heliosauth.models import User

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
  return reverse(password_login_view)

def get_user_info_after_auth(request):
  user = request.session['password_user']
  del request.session['password_user']
  user_info = user.info

  return {'type': 'password', 'user_id' : user.user_id, 'name': user.name, 'info': user.info, 'token': None}

def update_status(token, message):
  pass

def send_message(user_id, user_name, user_info, subject, body, attachments=[]):
  email = user_id
  name = user_name or user_info.get('name', email)
  recipient = formataddr((name, email))
  message = EmailMessage(subject, body, settings.SERVER_EMAIL, [recipient])
  for attachment in attachments:
      message.attach(*attachment)

  message.send(fail_silently=False)
