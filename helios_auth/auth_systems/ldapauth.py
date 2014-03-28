"""
LDAP Authentication
"""

from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from django_auth_ldap.backend import LDAPBackend

class LoginForm(forms.Form):
	username = forms.CharField(max_length=50)
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

			auth = LDAPBackend()
			user = auth.authenticate(username, password)

			request.session['ldap_user'] = user
			if user:
				return HttpResponseRedirect(reverse(after))
			else:
				error = _('Bad Username or Password')
	
	return render_template(request, 'password/login', {
		'form': form, 
		'error': error,
		'enabled_auth_systems': settings.AUTH_ENABLED_AUTH_SYSTEMS,
		})


def get_user_info_after_auth(request):
	return {
		'type': 'ldap', 
		'user_id' : request.session['ldap_user'].email, 
		'name': request.session['ldap_user'].first_name + ' ' + request.session['ldap_user'].last_name, 
		'info': {'email' : request.session['ldap_user'].email}, 
		'token': None 
		}


def get_auth_url(request, redirect_url = None):
  return reverse(ldap_login_view)


def send_message(user_id, user_name, user_info, subject, body):
    pass


def check_constraint(constraint, user_info):
	"""
	for eligibility
	"""
	pass