# -*- coding: utf-8 -*-
"""
LDAP Authentication
Author : shirlei@gmail.com
Version: 1.0
Requires libldap2-dev
django-auth-ldap 1.2.6
LDAP authentication relies on django-auth-ldap (http://pythonhosted.org/django-auth-ldap/),
which considers that "Authenticating against an external source is swell, but Django’s
auth module is tightly bound to a user model. When a user logs in, we have to create a model
object to represent them in the database."
Helios, originally, does not rely on default django user model. Discussion about that can be
found in:
https://groups.google.com/forum/#!topic/helios-voting/nRHFAbAHTNA
That considered, using a django plugin for ldap authentication, in order to not reinvent the
wheel seems ok, since it does not alter anything on original helios user model, it is just
for authentication purposes.
However, two installed_apps that are added when you first create a django project, which were
commented out in helios settings, need to be made available now:
django.contrib.auth
django.contrib.contenttypes'
This will enable the native django authentication support on what django-auth-ldap is build upon.
Further reference on
https://docs.djangoproject.com/en/1.8/topics/auth/
"""

from django import forms
from django.conf import settings
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _


from helios_auth.auth_systems.ldapbackend import backend


# some parameters to indicate that status updating is possible
STATUS_UPDATES = False


LOGIN_MESSAGE = _("Log in with my LDAP Account")

class LoginForm(forms.Form):
    username = forms.CharField(max_length=250)
    password = forms.CharField(widget=forms.PasswordInput(), max_length=100)


def ldap_login_view(request):
    from helios_auth.view_utils import render_template
    from helios_auth.views import after

    error = None

    if request.method == "GET":
            form = LoginForm()
    else:
            form = LoginForm(request.POST)
            
            request.session['auth_system_name'] = 'ldap'

            if request.POST.has_key('return_url'):
                request.session['auth_return_url'] = request.POST.get('return_url')

            if form.is_valid():
                username = form.cleaned_data['username'].strip()
                password = form.cleaned_data['password'].strip()

                auth = backend.CustomLDAPBackend()
                user = auth.authenticate(username, password)
                
                if user:
                    request.session['ldap_user']  = {
                        'username': user.username,
                        'email': user.email,
                        'name': user.first_name + ' ' + user.last_name,
                    }
                    return HttpResponseRedirect(reverse(after))
                else:
                    error = 'Bad Username or Password'

    return render_template(request, 'ldapauth/login', {
            'form': form,
            'error': error,
            'enabled_auth_systems': settings.AUTH_ENABLED_AUTH_SYSTEMS,
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
    send_mail(subject, body, settings.SERVER_EMAIL, ["%s <%s>" % (name, user_info['email'])],
            fail_silently=False, html_message=body)


def check_constraint(constraint, user_info):
    """
    for eligibility
    """
    pass


def can_create_election(user_id, user_info):
  return True
