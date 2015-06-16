"""
Shibboleth Authentication
author: Shirlei Chaves
e-mail: shirlei@gmail.com
version: 1.0 - 2015 
"""
import re

from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext as _



# some parameters to indicate that status updating is possible
STATUS_UPDATES = False


SHIBBOLETH_NATIVE_SP_ATTRIBUTES = ['Shib-Application-ID', 'Shib-Session-ID',
    'Shib-Authentication-Instant', 'Shib-Authentication-Method',
    'Shib-AuthnContext-Class', 'Shib-Session-Index'] # excluding Shib-Identity-Provider, since we need it


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

    shib_attrs, errors = parse_attributes(request.META)
    if errors:
        return render_template(request, 'shibboleth/missing_attributes', {
            'errors': errors,
        })

    if shib_attrs:
        request.session['shib_attrs'] = shib_attrs
        
        return HttpResponseRedirect(reverse(after))
    else:
        error = _('Bad Username or Password')

    return render_template(request, 'shibboleth/login_box', {
        'error': error,
	})
    

def get_user_info_after_auth(request):
    shib_user = request.session['shib_attrs']
    return {
		'type': 'shibboleth', 
		'user_id' : shib_user['email'], 
		'name': shib_user['common_name'], 
		'info': shib_user,
		'token': None,
		}


def get_auth_url(request, redirect_url = None):
  return reverse(shibboleth_login_view)


def send_message(user_id, user_name, user_info, subject, body):
    pass


def check_constraint(constraint, user):
    """
    Given a constraint list from the voters definition for some election,
    those constraints are checked against user attributes. In the first non-matching
    attribute, returns False
    """
    try:
        for key, value in constraint.items():
            # some user attributes may be multivalued
            user_attrs = re.split('[,;]',user.info['attributes'][key])
            ctr_list = re.split('[,;]',constraint[key])    
            has_attr = False
            for ctr in ctr_list:
                if ctr.strip() in user_attrs:
                    has_attr = True
            if not has_attr: # if one attribute isn't available, return False
                return False
    except KeyError:
        return False

    return True


def pretty_eligibility(constraint):
  pretty = _("Users with the following attributes:")
  pretty = pretty + "<ul>"
  for ctr in constraint:
    pretty = pretty + "<li>%s = %s </li>" % (ctr, constraint[ctr])
  return pretty + "</ul>" 


def generate_constraint(category_id, user):
  """
  generate the proper basic data structure to express a constraint
  based on the category string
  """
  constraints = {}
  for category in category_id:
    constraints[category] = category_id[category]
  return constraints

def eligibility_category_id(constraint):
  return constraint

def list_categories(user):
  attributes = user.info['attributes']
  return [{'id': str(y), 'name': '%s with the value  %s' % 
    (y, attributes[y])} for y in attributes] 


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
        if profile.django_user.groups.filter(name__in=settings.INSTITUTION_ROLE).exists():
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
         
    attributes = {}
    for value in META:
        if value.lower().startswith('shib-') and value not in SHIBBOLETH_NATIVE_SP_ATTRIBUTES:
            attr_name = value.split('-')[-1:][0]
            attributes[attr_name] = META[value]

    shib_attrs['attributes'] = attributes        

    return shib_attrs, errors
