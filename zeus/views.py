from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from django.template.loader import render_to_string
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

from heliosauth.security import get_user
from helios.view_utils import render_template

from helios.models import Election
from zeus.models import SecretAuthcode

def home(request):
  user = get_user(request)
  return render_template(request, "zeus/home", {'menu_active': 'home',
                                                        'user': user,
                                                'bad_login': request.GET.get('bad_login')})

def faqs_trustee(request):
  user = get_user(request)
  return render_template(request, "zeus/faqs_admin", {'menu_active': 'faqs',
                                                      'submenu': 'admin', 'user': user})
def faqs_voter(request):
  user = get_user(request)
  return render_template(request, "zeus/faqs_voter", {'menu_active': 'faqs',
                                                      'submenu': 'voter',
                                                        'user': user})
def resources(request):
  user = get_user(request)
  return render_template(request, "zeus/resources", {'menu_active': 'resources',
                                                     'user': user})

def stats(request):
    user = get_user(request)
    uuid = request.GET.get('uuid', None)
    election = None

    if uuid:
        election = Election.objects.filter(uuid=uuid)
        if not (user and user.superadmin_p):
          election = election.filter(is_completed=True)

        election = election.defer('encrypted_tally', 'result')[0]

    if user and user.superadmin_p:
      elections = Election.objects.filter(is_completed=True)
    else:
      elections = Election.objects.filter(is_completed=True)

    elections = elections.order_by('-created_at').defer('encrypted_tally',
                                                        'result')

    return render_template(request, 'zeus/stats', {'menu_active': 'stats',
                                                   'election': election,
                                                   'uuid': uuid,
                                                   'user': user,
                                                   'elections': elections})

def election_email_login(request, uuid):
    election = get_object_or_404(Election, uuid=uuid)
    return render_template(request, 'zeus/election_email_login', {'menu_active': 'home',
                                                   'election_o': election,
                                                   'bad_code': request.GET.get('bad_code', None)})

def election_email_show(request):
    if not request.method == 'POST':
        raise PermissionDenied

    uuid = request.POST.get('uuid', None)
    code = request.POST.get('secret', None)

    if not uuid or not code:
      raise PermissionDenied

    try:
      auth_code = SecretAuthcode.objects.get(election_uuid=uuid, code=code)
    except SecretAuthcode.DoesNotExist:
      return HttpResponseRedirect(reverse('zeus.views.election_email_login',
                                          kwargs={'uuid': uuid}) + "?bad_code=1")

    election = get_object_or_404(Election, uuid=uuid)
    voter_o = election.voter_set.get(voter_login_id=auth_code.voter_login)

    context = {'election': election, 'voter': voter_o}
    email_content = render_to_string("email/vote_body.txt", context)

    return render_template(request, 'zeus/election_email_show', {'menu_active': 'home',
                                                   'election_o': election,
                                                   'voter': voter_o,
                                                   'email_content': email_content})


