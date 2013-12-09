from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

from zeus.utils import render_template
from zeus import auth

from helios.models import Election


@auth.election_admin_required
def home(request):
    elections = Election.objects.administered_by(request.admin)

    # utility redirect
    if elections.count() == 0:
        return HttpResponseRedirect(reverse('election_create'))

    context = {
        'elections_administered': elections
    }
    return render_template(request, "index", context)
