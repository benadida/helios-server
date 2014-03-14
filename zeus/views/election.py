import urllib
import datetime
import json
import os

try:
  from collections import OrderedDict
except ImportError:
  from django.utils.datastructures import SortedDict as OrderedDict

from zeus.forms import ElectionForm
from zeus.forms import PollForm, PollFormSet
from zeus.utils import *
from zeus.views.utils import *
from zeus import tasks
from zeus import reports
from zeus import auth
from zeus.views.poll import voters_email

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.forms.models import modelformset_factory
from django.contrib import messages
from django.core import serializers
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_http_methods

from helios.view_utils import render_template
from helios.models import Election, Poll, CastVote, Voter


@transaction.commit_on_success
@auth.election_admin_required
@require_http_methods(["GET", "POST"])
def add_or_update(request, election=None):

    user = request.admin
    institution = user.institution

    if request.method == "GET":
        election_form = ElectionForm(institution, instance=election)
    else:
        election_form = ElectionForm(institution, request.POST,
                                     instance=election)

    if election_form.is_valid():
        with transaction.commit_on_success():
            election = election_form.save()
            if not election.admins.filter(pk=user.pk).count():
                election.admins.add(user)
            # TODO, make this optional ?
            if not election.has_helios_trustee():
                election.generate_trustee()
            if election.polls.count() == 0:
                url = election_reverse(election, 'polls_list')
            else:
                url = election_reverse(election, 'index')
            return HttpResponseRedirect(url)

    context = {'election_form': election_form, 'election': election}
    set_menu('election_edit', context)
    tpl = "election_new"
    if election and election.pk:
        tpl = "election_edit"
    return render_template(request, tpl, context)


@auth.election_user_required
@require_http_methods(["GET"])
def trustees_list(request, election):
    trustees = election.trustees.filter(election=election,
                                        secret_key__isnull=True)

    # TODO: can we move this in a context processor
    # or middleware ???
    voter = None
    poll = None
    if getattr(request, 'voter', None):
        voter = request.voter
        poll = voter.poll

    context = {
        'election': election,
        'poll': poll,
        'voter': voter,
        'trustees': trustees
    }
    set_menu('trustees', context)
    return render_template(request, 'election_trustees_list', context)


@auth.election_admin_required
@auth.requires_election_features('can_send_trustee_email')
@require_http_methods(["POST"])
def trustee_send_url(request, election, trustee_uuid):
    trustee = election.trustees.get(uuid=trustee_uuid)
    trustee.send_url_via_mail()
    url = election_reverse(election, 'trustees_list')
    return HttpResponseRedirect(url)


@auth.election_admin_required
@auth.requires_election_features('delete_trustee')
@transaction.commit_on_success
@require_http_methods(["POST"])
def trustee_delete(request, election, trustee_uuid):
    election.zeus.invalidate_election_public()
    trustee = election.trustees.get(uuid=trustee_uuid)
    trustee.delete()
    election.logger.info("Trustee %r deleted", trustee.email)
    election.zeus.compute_election_public()
    election.logger.info("Public key updated")
    url = election_reverse(election, 'trustees_list')
    return HttpResponseRedirect(url)


@auth.election_user_required
@require_http_methods(["GET"])
def index(request, election, poll=None):
    user = request.zeususer

    if poll:
        election_url = poll.get_absolute_url()
    else:
        election_url = election.get_absolute_url()

    booth_url = None
    if poll:
        booth_url = poll.get_booth_url(request)

    voter = None
    votes = None
    if user.is_voter:
        # cast any votes?
        voter = request.voter
        votes = voter.get_cast_votes()
        if election.frozen_at:
            voter.last_visit = datetime.datetime.now()
            voter.save()
        else:
            votes = None

    trustees = election.trustees.filter()

    context = {
        'election' : election,
        'poll': poll,
        'trustees': trustees,
        'user': user,
        'votes': votes,
        'election_url' : election_url,
        'booth_url': booth_url
    }
    if poll:
        context['poll'] = poll

    set_menu('election', context)
    return render_template(request, 'election_view', context)


@auth.election_admin_required
@auth.requires_election_features('can_freeze')
@require_http_methods(["POST"])
def freeze(request, election):
    election.logger.info("Starting to freeze")
    tasks.election_validate_create(election.id)
    
    # hacky delay. Hopefully validate create task will start running
    # before the election view redirect.
    import time
    time.sleep(4)

    url = election_reverse(election, 'index')
    return HttpResponseRedirect(url)


@auth.election_admin_required
@auth.requires_election_features('can_cancel')
@transaction.commit_on_success
@require_http_methods(["POST"])
def cancel(request, election):

    cancel_msg = request.POST.get('cancel_msg', '')
    cancel_date = datetime.datetime.now()

    election.canceled_at = cancel_date
    election.cancel_msg = cancel_msg
    election.completed_at = cancel_date

    election.save()
    url = election_reverse(election, 'index')
    return HttpResponseRedirect(url)


@auth.superadmin_required
@require_http_methods(["POST"])
def endnow(request, election):
    if election.voting_extended_until:
        election.voting_extended_until = datetime.datetime.now()
    else:
        election.voting_ends_at = datetime.datetime.now()
    election.save()
    election.logger.info("Changed election dates to be able to close voting")
    url = election_reverse(election, 'index')
    return HttpResponseRedirect(url)


@auth.election_admin_required
@auth.requires_election_features('can_close')
@transaction.commit_on_success
@require_http_methods(["POST"])
def close(request, election):
    election.close_voting()
    tasks.election_validate_voting(election.pk)
    url = election_reverse(election, 'index')
    return HttpResponseRedirect(url)


@auth.election_admin_required
@auth.requires_election_features('can_validate_voting')
@transaction.commit_on_success
@require_http_methods(["POST"])
def validate_voting(request, election):
    tasks.election_validate_voting(election_id=election.id)
    url = election_reverse(election, 'index')
    return HttpResponseRedirect(url)


@auth.election_admin_required
@auth.requires_election_features('can_mix')
@transaction.commit_on_success
@require_http_methods(["POST"])
def start_mixing(request, election):
    tasks.start_mixing.delay(election_id=election.id)
    url = election_reverse(election, 'index')
    return HttpResponseRedirect(url)


@auth.election_admin_required
@auth.election_view()
@require_http_methods(["GET"])
def report(request, election, format):
    reports_list = request.GET.get('report',
                                   'election,voters,votes,results').split(",")

    _reports = OrderedDict()
    if 'election' in reports_list:
        _reports['election'] = list(reports.election_report([election],
                                                            True, False))
    if 'voters' in reports_list:
        _reports['voters'] = list(reports.election_voters_report([election]))
    if 'votes' in reports_list:
        _reports['votes'] = list(reports.election_votes_report([election],
                                                               True, True))
    if 'results' in reports_list:
        _reports['results'] = list(reports.election_results_report([election]))

    if format == "html":
        return render_template(request, "election_report", {
            'election': election,
            'reports': _reports,
        })
    else:
        def handler(obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            raise TypeError

        return HttpResponse(json.dumps(_reports, default=handler),
                            mimetype="application/json")


@auth.election_admin_required
@auth.requires_election_features('polls_results_computed')
@require_http_methods(["GET"])
def results_file(request, election, ext='pdf', shortname=''):

    fpath = election.get_results_file_path(ext)

    if not os.path.exists(fpath):
        election.compute_results_status = 'pending'
        election.save()
        election.compute_results()

    if request.GET.get('gen', None):
        election.compute_results_status = 'pending'
        election.save()
        election.compute_results()

    if not os.path.exists(fpath):
        raise Http404

    if settings.USE_X_SENDFILE:
        response = HttpResponse()
        response['Content-Type'] = ''
        response['X-Sendfile'] = fpath
        return response
    else:
        data = file(fpath, 'r')
        response = HttpResponse(data.read(), mimetype='application/%s' % ext)
        data.close()
        basename = os.path.basename(fpath)
        response['Content-Dispotition'] = 'attachment; filename=%s' % basename
        return response


@auth.superadmin_required
@auth.election_view()
@require_http_methods(["GET"])
def json_data(request, election):
    if not election.trial:
        raise PermissionDenied('33')
    election_json = serializers.serialize("json", [election])
    polls_json = serializers.serialize("json", election.polls.all())
    trustees_json = serializers.serialize("json", election.trustees.all())
    voters_json = serializers.serialize("json",
                                        Voter.objects.filter(poll__election=election))
    json = """{"election":%s, "polls": %s,
               "trustees": %s, "voters": %s}""" % (election_json,
                                                   polls_json,
                                                   trustees_json,
                                                   voters_json)
    return HttpResponse(json, mimetype="application/json")


def test_cookie(request):
    continue_url = request.GET['continue_url']
    request.session.set_test_cookie()
    next_url = "%s?%s" % (reverse('test_cookie_2'),
                          urllib.urlencode({'continue_url': continue_url}))
    return HttpResponseRedirect(next_url)


def test_cookie_2(request):
    continue_url = request.GET['continue_url']

    if not request.session.test_cookie_worked():
        return HttpResponseRedirect("%s?%s" % (reverse('nocookies'),
                                               urllib.urlencode({
                                                   'continue_url':
                                                   continue_url})))

    request.session.delete_test_cookie()
    return HttpResponseRedirect(continue_url)


def nocookies(request):
    retest_url = "%s?%s" % (reverse('test_cookie'),
                            urllib.urlencode({
                            'continue_url' : request.GET['continue_url']}))
    return render_template(request, 'nocookies', {'retest_url': retest_url})
