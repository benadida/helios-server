"""
Phone number authentication, for voters only: a voter whose number is on a
voter list logs in with a one-time code sent to them by text message.
"""

import logging
import re
import secrets
import time

from django import forms
from django.conf import settings
from django.db import transaction
from django.http import Http404, HttpResponseRedirect
from django.urls import re_path, reverse
from django.utils.crypto import constant_time_compare, salted_hmac

from helios_auth import sms, url_names

STATUS_UPDATES = False
PHONE_LOGIN_URL_NAME = "auth@phone@login"
PHONE_VERIFY_URL_NAME = "auth@phone@verify"

LOGIN_CODE_LIFETIME = 600
LOGIN_CODE_MAX_ATTEMPTS = 5
LOGIN_CODE_RESEND_INTERVAL = 60

logger = logging.getLogger(__name__)

def normalize_user_id(value):
  """
  international format, e.g. +15551234567, ignoring spaces, dashes, dots and brackets
  """
  number = re.sub(r'[\s().-]', '', value or '')
  if not re.fullmatch(r'\+[1-9]\d{6,14}', number):
    raise ValueError("invalid phone number '%s', use the international format, e.g. +15551234567" % value)
  return number

class PhoneLoginForm(forms.Form):
  number = forms.CharField(label="Phone number", max_length=30)

class PhoneCodeForm(forms.Form):
  code = forms.CharField(label="Code", max_length=10)

def _check_enabled():
  if 'phone' not in settings.AUTH_ENABLED_SYSTEMS:
    raise Http404()

def _code_hash(number, code):
  return salted_hmac('helios_auth.phone.login_code', "%s:%s" % (number, code)).hexdigest()

def _locked_user(number):
  from helios_auth.models import User
  return User.objects.select_for_update().filter(user_type='phone', user_id=number).first()

def _send_login_code(number):
  """
  text a new code, only to numbers already on a voter list
  """
  with transaction.atomic():
    user = _locked_user(number)
    if not user:
      return

    info = dict(user.info or {})
    now = time.time()
    if now < info.get('login_code_sent_at', 0) + LOGIN_CODE_RESEND_INTERVAL:
      return

    code = "%06d" % secrets.randbelow(10**6)
    info.update({'login_code_hash': _code_hash(number, code), 'login_code_sent_at': now, 'login_code_attempts': 0})
    user.info = info
    user.save()

    sms.send_sms(number, "Your %s login code is %s. It expires in %d minutes." % (settings.SITE_TITLE, code, LOGIN_CODE_LIFETIME // 60))

def _check_login_code(number, code):
  with transaction.atomic():
    user = _locked_user(number)
    info = dict(user.info or {}) if user else {}
    if 'login_code_hash' not in info:
      return False
    if time.time() > info['login_code_sent_at'] + LOGIN_CODE_LIFETIME or info['login_code_attempts'] >= LOGIN_CODE_MAX_ATTEMPTS:
      return False

    matches = constant_time_compare(info['login_code_hash'], _code_hash(number, code))
    if matches:
      del info['login_code_hash']
    else:
      info['login_code_attempts'] += 1
    user.info = info
    user.save()
    return matches

def phone_login_view(request):
  from helios_auth.security import check_csrf
  from helios_auth.view_utils import render_template

  _check_enabled()

  if request.method == "GET":
    return render_template(request, 'phone/login', {'form': PhoneLoginForm()})

  check_csrf(request)
  request.session['auth_system_name'] = 'phone'

  form = PhoneLoginForm(request.POST)
  try:
    if not form.is_valid():
      raise ValueError()
    number = normalize_user_id(form.cleaned_data['number'])
  except ValueError:
    return render_template(request, 'phone/login', {'form': form, 'error': 'Enter your number in international format, e.g. +15551234567.'})

  try:
    _send_login_code(number)
  except Exception:
    logger.warning("could not send a login code to %s", number, exc_info=True)
    return render_template(request, 'phone/login', {'form': form, 'error': "We couldn't send a text message. Please try again later."})

  request.session['phone_login_number'] = number
  return HttpResponseRedirect(reverse(PHONE_VERIFY_URL_NAME))

def phone_verify_view(request):
  from helios_auth.security import check_csrf
  from helios_auth.view_utils import render_template

  _check_enabled()

  number = request.session.get('phone_login_number')
  if not number:
    return HttpResponseRedirect(reverse(PHONE_LOGIN_URL_NAME))

  if request.method == "GET":
    return render_template(request, 'phone/verify', {'form': PhoneCodeForm(), 'number': number})

  check_csrf(request)

  form = PhoneCodeForm(request.POST)
  if form.is_valid() and _check_login_code(number, form.cleaned_data['code'].strip()):
    del request.session['phone_login_number']
    request.session['phone_user_id'] = number
    return HttpResponseRedirect(reverse(url_names.AUTH_AFTER))

  return render_template(request, 'phone/verify', {'form': PhoneCodeForm(), 'number': number, 'error': 'Wrong or expired code.'})

def get_auth_url(request, redirect_url=None):
  return reverse(PHONE_LOGIN_URL_NAME)

def get_user_info_after_auth(request):
  from helios_auth.models import User
  user = User.get_by_type_and_id('phone', request.session.pop('phone_user_id'))
  return {'type': 'phone', 'user_id': user.user_id, 'name': user.name, 'info': user.info, 'token': None}

def update_status(token, message):
  pass

def send_message(user_id, name, user_info, subject, body):
  sms.send_sms(user_id, body.strip())

def can_create_election(user_id, user_info):
  return False

urlpatterns = [
  re_path(r'^phone/login$', phone_login_view, name=PHONE_LOGIN_URL_NAME),
  re_path(r'^phone/verify$', phone_verify_view, name=PHONE_VERIFY_URL_NAME),
]
