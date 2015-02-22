"""
Shibboleth Authentication
author: Shirlei Chaves
e-mail: shirlei@gmail.com
version: 1.0 - 2015 

"""

from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext as _


# some parameters to indicate that status updating is possible
STATUS_UPDATES = False


class LoginForm(forms.Form):
	username = forms.CharField(max_length=50)
	password = forms.CharField(widget=forms.PasswordInput(), max_length=100)


def shibboleth_login_view(request):
	from helios_auth.view_utils import render_template
	
	error = None

	return render_template(request, 'shibboleth/login_box', {
		'error': error,
		'enabled_auth_systems': settings.AUTH_ENABLED_AUTH_SYSTEMS,
	})


def shibboleth_register(request):
    from helios_auth.view_utils import render_template
    from helios_auth.views import after
    user, error = parse_attributes(request.META)
    if user:
        request.session['shib_user'] = user
        return HttpResponseRedirect(reverse(after))
    else:
        error = _('Bad Username or Password')

    return render_template(request, 'shibboleth/login_box', {
        'error': error,
	})
    

def get_user_info_after_auth(request):
    user = request.session['shib_user']
    del request.session['shib_user']
    return {
		'type': 'shibboleth', 
		'user_id' : user['email'], 
		'name': user['common_name'], 
		'info': {'email' : user['email']}, 
		'token': None 
		}


def get_auth_url(request, redirect_url = None):
  return reverse(shibboleth_login_view)


def send_message(user_id, user_name, user_info, subject, body):
    pass


def check_constraint(constraint, user_info):
	"""
	for eligibility
	"""
	pass

"""
Function obtained from 
https://github.com/sorrison/django-shibboleth/blob/6967298fa9e659f5a08d2736e652997ae4f1d2f5/django_shibboleth/utils.py
"""
def parse_attributes(META):
    shib_attrs = {}
    error = False
    for header, attr in settings.SHIBBOLETH_ATTRIBUTE_MAP.items():
        required, name = attr
        values = META.get(header, None)
        value = None
        if values:
            # If multiple attributes releases just care about the 1st one
            try:
                value = values.split(';')[0]
            except:
                value = values

        shib_attrs[name] = value
        if not value or value == '':
            if required:
                error = True
    return shib_attrs, error

def shibboleth_meta(request):

    from helios_auth.view_utils import render_template
    meta_data = request.META.items()
    
    return render_template(request, 'shibboleth/meta', {
        'meta_data': meta_data,
	})
