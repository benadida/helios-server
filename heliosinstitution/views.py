from django.views.decorators.http import require_http_methods


from helios_auth.security import *
from heliosinstitution.models import InstitutionUserProfile


from view_utils import *

def home(request):
    pass

@login_required
def manage_users(request):  
    user = get_user(request)
    institution = user.authuserprofile_set.get().institution
    users = InstitutionUserProfile.objects.filter(institution=institution)

    if request.method == "GET":
        return render_template(request, "manage_users", {
            "users": users,
            "institution": institution,
        })


@login_required
@require_http_methods(["POST",])
def delegate_institution_admin(request, institution_id):
    """
    Delegate an user to administer institution
    """
    user = get_user(request)
    pass


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
    pass


@login_required
@require_http_methods(["POST",])
def revoke_election_admin(request, institution_id):
    """
    Revoke an user as elections admin
    """
    user = get_user(request)
    pass
