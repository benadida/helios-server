# -*- coding: utf-8 -*-
"""
LDAP Authentication
Author : shirlei@gmail.com
Version: 2.0
LDAP authentication relies on django-auth-ldap (https://django-auth-ldap.readthedocs.io/)
"""

from django import forms
from django.conf import settings
from django.conf.urls import url
from django.core.mail import send_mail
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

# some parameters to indicate that status updating is possible
STATUS_UPDATES = False

LDAP_LOGIN_URL_NAME = "auth@ldap@login"
LOGIN_MESSAGE = _("Log in with my LDAP Account")

class LoginForm(forms.Form):
    username = forms.CharField(max_length=250)
    password = forms.CharField(widget=forms.PasswordInput(), max_length=100)


def ldap_login_view(request):
    from helios_auth.view_utils import render_template
    from helios_auth.views import after
    from helios_auth.auth_systems.ldapbackend import backend

    error = None

    if request.method == "GET":
        form = LoginForm()
    else:
        form = LoginForm(request.POST)

        request.session['auth_system_name'] = 'ldap'

        if 'return_url' in request.POST:
            request.session['auth_return_url'] = request.POST.get('return_url')

        if form.is_valid():
            username = form.cleaned_data['username'].strip()
            password = form.cleaned_data['password'].strip()

            auth = backend.CustomLDAPBackend()
            user = auth.authenticate( None, username=username, password=password)

            if user:
                request.session['ldap_user'] = {
                    'username': user.username,
                    'email': user.email,
                    'name': f'{user.first_name} {user.last_name}',
                }
                return HttpResponseRedirect(reverse(after))
            else:
                error = 'Bad Username or Password'

    return render_template(request, 'ldapauth/login', {
            'form': form,
            'error': error,
            'enabled_auth_systems': settings.AUTH_ENABLED_SYSTEMS,
        })


def get_user_info_after_auth(request):
    return {
       'type': 'ldap',
       'user_id' : request.session['ldap_user']['username'],
       'name': request.session['ldap_user']['name'],
       'info': {'email': request.session['ldap_user']['email']},
       'token': None
    }


def get_auth_url(request, redirect_url = None):
    return reverse(ldap_login_view)


def send_message(user_id, name, user_info, subject, body):
    send_mail(
        subject,
        body,
        settings.SERVER_EMAIL,
        [f"{name} <{user_info['email']}>"],
        fail_silently=False,
        html_message=body,
    )


def check_constraint(constraint, user_info):
    """
    for eligibility
    """
    pass


def can_create_election(user_id, user_info):
  return True

urlpatterns = [url(r'^ldap/login', ldap_login_view, name=LDAP_LOGIN_URL_NAME)]
