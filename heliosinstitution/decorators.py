from functools import update_wrapper

from django.core.exceptions import *
from django.utils.translation import ugettext as _

from helios_auth.security import get_user


def require_institution_admin(func):
    def require_institution_admin_wrapper(request, *args, **kw):
        from heliosinstitution.models import InstitutionUserProfile
        user = get_user(request)
        # TODO: check if user is active
        if not user:
            raise PermissionDenied(_("You don't have permission to access this view"))
        try:
            user.institutionuserprofile_set.get().django_user.groups.filter(
                    name='Institution Admin')
        except InstitutionUserProfile.DoesNotExist:
                raise PermissionDenied(_("You don't have permission to access this view"))
            
        return func(request, *args, **kw)

    return update_wrapper(require_institution_admin_wrapper, func)
