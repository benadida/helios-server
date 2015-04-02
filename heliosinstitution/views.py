import json

from django.views.decorators.http import require_http_methods
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User as DjangoUser, Group
from django.utils.translation import ugettext as _


from helios_auth.security import *
from heliosinstitution.models import InstitutionUserProfile
from heliosinstitution.decorators import *


from view_utils import *

def home(request):
    pass

@login_required
@require_institution_admin
@require_http_methods(["GET",])
def manage_users(request):  
    user = get_user(request)
    institution = user.institutionuserprofile_set.get().institution

    return render_template(request, "manage_users", {
        "institution": institution,
    })


@login_required
@require_institution_admin
@require_http_methods(["POST",])
def delegate_user(request, role):
    """
    Delegate an user to administer institution
    """
    user = get_user(request)
    email = request.POST.get('email', '') 
    status = 200
    if email:
        try:
            # let's se if we already have this email for this institution
            institution_user_profile = InstitutionUserProfile.objects.get(email=email, 
                institution=user.institutionuserprofile_set.get().institution)
        except InstitutionUserProfile.DoesNotExist:
            # no, we don't, lets create one
            django_user = DjangoUser.objects.create(email=email,username=email)
            django_user.save()
            institution_user_profile = InstitutionUserProfile.objects.create(email=email, 
                institution=user.institutionuserprofile_set.get().institution,
                django_user=django_user)
            institution_user_profile.save()
    
        g = Group.objects.get(name=role)
        g.user_set.add(institution_user_profile.django_user)

        #TODO: log error
        response_data = {'success': _('E-mail successfully saved')}
    else:
        response_data = {'error': _('An e-mail must be informed')} 
        status = 400
    return HttpResponse(json.dumps(response_data), content_type="application/json", status=status)


@login_required
@require_institution_admin
@require_http_methods(["POST",])
def revoke_user(request, user_pk):
    """
    Revoke an institution user
    """
    user = get_user(request)
    status = 200
    try:
        # let's se if we already have this email for this institution
        profile = InstitutionUserProfile.objects.get(pk=user_pk, 
            institution=user.institutionuserprofile_set.get().institution)
        profile.django_user.delete()
        # not deleting helios user, just removing admin_p, since it can still be a voter and so on
        profile.helios_user.admin_p = False
        profile.helios_user.save()
        profile.delete()
        response_data = {'success': _('User successfully removed')} 
    except InstitutionUserProfile.DoesNotExist:
        response_data = {'error': _('User not found')} 
        status = 400

    return HttpResponse(json.dumps(response_data), content_type="application/json", status=status)


@login_required
@require_institution_admin
@require_http_methods(["GET",])
def users(request):
    user = get_user(request)
    institution = user.institutionuserprofile_set.get().institution
    return render_template(request, "institution_users", {
        "institution": institution,
    })
