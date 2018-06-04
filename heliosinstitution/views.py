import copy
import json

from django.views.decorators.http import require_http_methods
from django.http import HttpResponseRedirect, HttpResponse
from django.conf import settings
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User as DjangoUser, Group
from django.utils.translation import ugettext as _

from helios.models import Election
from helios.security import can_create_election
from helios_auth.security import *
import helios_auth.views as auth_views
from heliosinstitution.models import InstitutionUserProfile, Institution
from heliosinstitution.decorators import *
from helioslog.models import HeliosLog


from view_utils import *
from heliosinstitution import utils


def home(request):

    # load the featured elections
    elections = Election.objects.all().order_by('-created_at')
  
    user = get_user(request)
    create_p = can_create_election(request)

    elections_administered = Election.get_by_user_as_admin(user, archived_p=False, limit=5)

    if user:
        elections_voted = Election.get_by_user_as_voter(user, limit=5)
    else:
        elections_voted = None

    institutions = Institution.objects.all()
 
    institutions_list = []

    for institution in institutions:
        institutions_list.append({
            'pk': institution.pk,
            'name': institution.name,
            'elections_new': institution.elections_new(),
            'elections_in_progress' : institution.elections_in_progress(),
            'elections_done': institution.elections_done(),
        })

    return render_template(request, "index", {'elections': elections,
                                            'elections_administered' : elections_administered,
                                            'elections_voted' : elections_voted,
                                            'create_p':create_p,
                                            'institutions': institutions_list})

@login_required
@require_institution_admin
def dashboard(request):
    if request.method == 'GET':
        user = get_user(request)
        institution = user.institutionuserprofile_set.get().institution

    return render_template(request, "dashboard", {
        "institution": institution,
    })


@login_required
@require_institution_admin
def stats(request):
    user = get_user(request)
    institution = user.institutionuserprofile_set.get().institution
    num_votes_in_queue = 0
    #TODO: actually count the number of votes in queue!
    return render_template(request, "stats", {
        "institution": institution,
         "num_votes_in_queue": num_votes_in_queue,
    })


@login_required
@require_institution_admin
def recent_cast_votes(request):
    user = get_user(request)
    institution = user.institutionuserprofile_set.get().institution
    
    return render_template(request, "stats", {
        "institution": institution,
    })


@login_required
@require_institution_admin
@require_http_methods(["POST",])
def add_expires_at(request, user_pk):
    user = get_user(request)
    expires_at = request.POST.get('expires_at', '') 
    status = 400
    from datetime import datetime
    valid_expires_at = None
    
    try:
        valid_expires_at = datetime.strptime(request.POST.get('expires_at', ''),
            '%d/%m/%Y')
    except ValueError:
        response_data = {'error': _('Please, provide a valid expires at value')}

    if user:
        try:
            institution_user_profile = InstitutionUserProfile.objects.get(pk=user_pk, 
                institution=user.institutionuserprofile_set.get().institution)

            if valid_expires_at:
                institution_user_profile.expires_at = valid_expires_at

            institution_user_profile.save()

            response_data = {'success': _('Expires at successfully saved.' )}
            status = 200
        
        except Exception:
            response_data = {'error': _('Something went wrong, please try again.')}
    else:
        response_data = {'error': _('An e-mail must be informed')} 
    
    return HttpResponse(json.dumps(response_data), content_type="application/json", 
        status=status)


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
            #using for username just first 30 caracteres allowed by django
            django_user = DjangoUser.objects.create(email=email,username=email[0:30])
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
        if profile.helios_user is not None:
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


@login_required
@require_institution_admin
@require_http_methods(["GET",])
def admin_actions(request):
    user = get_user(request)
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 25))
    actions = HeliosLog.objects.filter(user=user).order_by('-at')
    actions_paginator = Paginator(actions, limit)
    actions_page = actions_paginator.page(page)

    return render_template(request, "stats_admin_actions", {'actions' : actions_page.object_list, 'actions_page': actions_page,
                                                      'limit' : limit})


@login_required
def user_metadata(request, user_pk):
    user = get_user(request)
    user_metadata = {}
    if user.pk == int(user_pk):
        user_metadata = user.info

    return render_template(request,"user_metadata",{"user_metadata": user_metadata})


def elections_by_year(request, year=None):
    user = get_user(request)
    if year is not None:
        elections = Election.objects.filter(created_at__year=2014).order_by('-created_at')
    else:
        elections = Election.objects.all().order_by('-created_at')
    return HttpResponse(json.dumps(
        {'elections': 
            [{'election.pk': election.pk, 'election.name': election.name} for election in elections ]
        }), 
        content_type="application/json", status=200)


@require_http_methods(["GET",])
def elections_by_type_year(request, institution_pk, type=None, year=None):
    user = get_user(request)
    try:
	institution = Institution.objects.get(pk=institution_pk)
        status = 200
        if type == 'new':
            response_data = {'success': _('Success'), 'elections': institution.elections_new(year) }
        elif type =='in_progress':
            response_data = {'success': _('Success'), 'elections': institution.elections_in_progress(year) }
        elif type == 'done':
            response_data = {'success': _('Success'), 'elections': institution.elections_done(year) }
        else:
            response_data = {'success': _('Success'), 'elections': institution.elections}
    except Institution.DoesNotExist:
        status = 400
        response_data = {'error' : _("Institution does not exist")}

    return HttpResponse(json.dumps(response_data), 
        content_type="application/json", status=200)


@require_http_methods(["GET",])
def elections_summary(request, year=None):
    institutions = Institution.objects.all()
    institutions_list = []

    for institution in institutions:
        institutions_list.append({
        'pk': institution.pk,
        'name': institution.name,
        'elections_new': institution.elections_new(year),
        'elections_in_progress' : institution.elections_in_progress(year),
        'elections_done': institution.elections_done(year),
    })

    return render_template(request, "elections_summary", {
        "institutions": institutions_list,
    })

@login_required
@require_institution_admin
def institution_details(request, institution_pk):
    institution = Institution.objects.get(id=institution_pk)
    for data in request.POST:
        setattr(institution, data, request.POST[data])
    institution.save()
    return render_template(request, "institution_details", {
        "institution": institution,
    })


@login_required
def elections_administered(request, user_pk):
    user = get_user(request)
    elections_administered = []
    if user.pk == int(user_pk):
        elections_administered = utils.elections_as_json(Election.get_by_user_as_admin(user))
    return render_template(request, "elections_administered", {
        "elections_administered": elections_administered,
    })

