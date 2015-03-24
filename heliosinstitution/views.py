import json

from django.views.decorators.http import require_http_methods
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _


from helios_auth.security import *
from heliosinstitution.models import InstitutionUserProfile


from view_utils import *

def home(request):
    pass

@login_required
@require_http_methods(["GET",])
def manage_users(request):  
    user = get_user(request)
    institution = user.institutionuserprofile_set.get().institution

    return render_template(request, "manage_users", {
        "institution": institution,
    })


@login_required
@require_http_methods(["POST",])
def delegate_institution_admin(request, institution_id):
    """
    Delegate an user to administer institution
    """
    user = get_user(request)
    email = request.POST.get('email', '') 
    status = 200
    if email:
        if user.institutionuserprofile_set.get().is_institution_admin:
            institution_user_profile, created = InstitutionUserProfile.objects.get_or_create(email=email, 
                institution=user.institutionuserprofile_set.get().institution)
            institution_user_profile.save()
            #TODO: add to institution admin group
            #TODO: log error
            response_data = {'success': _('E-mail successfully saved')}
    else:
        response_data = {'error': _('An e-mail must be informed')} 
        status = 400
    return HttpResponse(json.dumps(response_data), content_type="application/json", status=status)
    


@login_required
@require_http_methods([ "POST,"])
def revoke_institution_admin(request, institution_id):
    """
    Revoke an user as institution admin
    """
    user = get_user(request)
    pass


@login_required
@require_http_methods(["POST",])
def delegate_election_admin(request, institution_id):
    """
    Enable an user to administer elections
    """
    user = get_user(request)
    email = request.POST.get('email', '') 
    status = 200
    if email:
        if user.institutionuserprofile_set.get().is_institution_admin:
            institution_user_profile, created = InstitutionUserProfile.objects.get_or_create(email=email, 
                institution=user.institutionuserprofile_set.get().institution)
            institution_user_profile.save()
            #TODO: add to institution admin group
            #TODO: log error
            response_data = {'success': _('E-mail successfully saved')}
    else:
        response_data = {'error': _('An e-mail must be informed')} 
        status = 400
    return HttpResponse(json.dumps(response_data), content_type="application/json", status=status)
    pass


@login_required
@require_http_methods(["POST",])
def revoke_election_admin(request, institution_id):
    """
    Revoke an user as elections admin
    """
    user = get_user(request)
    pass


@login_required
@require_http_methods(["GET",])
def users(request):
    user = get_user(request)
    institution = user.institutionuserprofile_set.get().institution
    return render_template(request, "institution_users", {
        "institution": institution,
    })
