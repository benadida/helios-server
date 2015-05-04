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

    user, errors = parse_attributes(request.META)

    if errors:
        return render_template(request, 'shibboleth/missing_attributes', {
            'errors': errors,
        })

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
		'info': user, 
		'token': None,
		}


def get_auth_url(request, redirect_url = None):
  return reverse(shibboleth_login_view)


def send_message(user_id, user_name, user_info, subject, body):
    pass


def check_constraint(constraint, user):
    """
    for eligibility
    """
    for key, value in constraint.items():
        if constraint[key] != user.info[key]:
            return False
    return True
    

def user_needs_intervention(user_id, user_info, token):
    """
    check to see if user is following the users we need
    """
    from heliosinstitution.models import Institution, InstitutionUserProfile
    from helios_auth.models import User

    try:
        helios_user = User.objects.get(user_id=user_id, user_type='shibboleth')

        profile = InstitutionUserProfile.objects.get(email=user_info['email'])
        
        profile.helios_user = helios_user
        profile.active = True

        # check if user has a role
        # TODO: check the use of cached properties
        if profile.django_user.groups.filter(name__in=['Institution Admin','Election Admin']).exists():
            profile.helios_user.admin_p = True    
        
        if profile.is_institution_admin:
            # let's check/save idp address
            if profile.institution.idp_address != user_info['identity_provider']:
                profile.institution.idp_address = user_info['identity_provider']
                profile.institution.save()
        profile.helios_user.save()
        profile.save()

    except User.DoesNotExist:
        # something went really wrong with the authentication...
        # TODO return logout url
        pass
    except InstitutionUserProfile.DoesNotExist:
        # the given user does not have a institution role assigned
        # TODO check if he/she has another role
        pass

    return None

"""
Function based on 
https://github.com/sorrison/django-shibboleth/blob/6967298fa9e659f5a08d2736e652997ae4f1d2f5/django_shibboleth/utils.py
"""
def parse_attributes(META):
    shib_attrs = {}
    errors = []
    for header, attr in settings.SHIBBOLETH_ATTRIBUTE_MAP.items():
        required, name = attr
        values = META.get(header, None)
        value = None
        if values:
            # If multiple attributes releases just care about the 1st one
            try:
                value = values.split(';')[0]
            except:
                pass
        shib_attrs[name] = value
        if value is None or value == '':
            if required:
                errors.append(name)
    
    for value in META:
        if value.lower().startswith('shib-'):
            shib_attrs[value] = META[value]

    return shib_attrs, errors
