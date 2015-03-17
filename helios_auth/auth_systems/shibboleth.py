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

#from heliosinstitution.models import Institution


# some parameters to indicate that status updating is possible
STATUS_UPDATES = False


class LoginForm(forms.Form):
	username = forms.CharField(max_length=50)
	password = forms.CharField(widget=forms.PasswordInput(), max_length=100)


def shibboleth_login_view(request):
	#from helios_auth.view_utils import render_template
	
	#error = None

	#return render_template(request, 'shibboleth/login_box', {
	#	'error': error,
	#	'enabled_auth_systems': settings.AUTH_ENABLED_AUTH_SYSTEMS,
	#})
    return HttpResponseRedirect(reverse(shibboleth_register))


def shibboleth_register(request):
    from helios_auth.view_utils import render_template
    from helios_auth.views import after

    #user, error = parse_attributes(request.META)
    user = {'email': 'shirlei@gmail.com',
    'type': 'shibboleth',
    'common_name': 'Shirlei',
    'identity_provider': 'https://idp1.cafeexpresso.rnp.br/idp/shibboleth',
    'user_id': 'shirlei@gmail.com'}
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
		'info': {
            'email' : user['email'],
            'identity_provider': user['identity_provider'],
         }, 
		'token': None,
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

def user_needs_intervention(user_id, user_info, token):
    """
    check to see if user is following the users we need
    """
    from heliosinstitution.models import Institution, InstitutionUserProfile
    from helios_auth.models import User

    try:
        user = User.objects.get(user_id=user_id, user_type='shibboleth')

        institution = Institution.objects.get(mngt_email=user_info['email'])
        if institution.idp_address != user_info['identity_provider']:
            institution.idp_address = user_info['identity_provider']
            institution.save()

        profile, created = InstitutionUserProfile.objects.get_or_create(institution=institution, 
            user=user, email=user_info['email'])
        profile.active = True
        profile.user.admin_p = True    
        profile.user.save()
        profile.save()
        return None
    except User.DoesNotExist:
        # something went really wrong with the authentication...
        # TODO return logout url
        pass
    except Institution.DoesNotExist:
        # the given user does not manager, maybe is another type...
        # TODO check if he/she has another role

        pass
    else:
        return None

    try:    
        institution = Institution.objects.get(identity_provider=user_info['identity_provider'])
        profile = InstitutionUserProfile.objects.get(institution=institution, 
            email=user_info['email'])
        profile.active = True
        profile.user = user
        profile.save()
    except:
        pass
  
    return None

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
