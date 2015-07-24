import simplejson
import logging
import datetime
import json

from django.conf.urls.defaults import *
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _
from django.contrib import messages

from zeus.forms import ElectionForm
from zeus import auth
from zeus.utils import *
from zeus.views.utils import *
from zeus.views.common import *

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse
from django.views.decorators.http import require_http_methods

from helios.view_utils import render_template
from helios.models import Election, Trustee
from heliosauth import utils
from helios.crypto import algs

logger = logging.getLogger()


@auth.election_view(check_access=False)
@auth.requires_election_features('trustee_can_login')
@require_http_methods(['GET'])
def login(request, election, trustee_email, trustee_secret):
    trustee = get_object_or_404(Trustee, election=election,
                                email=trustee_email)
    if not trustee:
        raise PermissionDenied("Invalid election")

    if trustee_secret == trustee.secret:
        user = auth.ZeusUser(trustee)
        if request.zeususer.is_authenticated() and (
                not request.zeususer.is_trustee or \
                    request.zeususer._user.pk != trustee.pk):
            messages.error(request,
                           _("You need to logout from your current account "
                             "to access this view."))
            return HttpResponseRedirect(reverse('error', kwargs={'code': 403}))

        user.authenticate(request)
        election.logger.info("Trustee %r logged in", trustee.email)
        return HttpResponseRedirect(reverse('election_trustee_home',
                                            args=[election.uuid]))

@auth.trustee_view
@auth.requires_election_features('trustee_can_generate_key')
@require_http_methods(['GET'])
def keygen(request, election, trustee):
    eg_params_json = simplejson.dumps(ELGAMAL_PARAMS_LD_OBJECT.toJSONDict(),
                                      sort_keys=True)
    context = {
        'eg_params_json': eg_params_json,
        'election': election,
        'trustee': trustee
    }
    return render_template(request, "election_trustee_keygen", context)


@auth.trustee_view
@auth.requires_election_features('trustee_can_check_sk')
@require_http_methods(['GET'])
def check_sk(request, election, trustee):
    context = {
        'election': election,
        'trustee': trustee
    }
    return render_template(request, 'election_trustee_check_sk', context)


@auth.trustee_view
@auth.requires_election_features('trustee_can_check_sk')
@require_http_methods(['POST'])
def verify_key(request, election, trustee):
    context = {
        'election': election,
        'trustee': trustee
    }
    election.reprove_trustee(trustee)
    return render_template(request, 'election_trustee_check_sk', context)


@auth.trustee_view
@transaction.commit_manually
@auth.requires_election_features('trustee_can_upload_pk')
@require_http_methods(['POST'])
def upload_pk(request, election, trustee):
    try:
        public_key_and_proof = \
                utils.from_json(request.POST['public_key_json'])
        public_key = algs.EGPublicKey.fromJSONDict(
            public_key_and_proof['public_key'])
        pok = algs.DLogProof.fromJSONDict(public_key_and_proof['pok'])
        election.add_trustee_pk(trustee, public_key, pok)
        transaction.commit()
    except Exception, e:
        election.logger.exception(e)
        transaction.rollback()
        messages.error(request, "Cannot upload public key")

    return HttpResponseRedirect(reverse('election_trustee_home',
                                        args=[election.uuid]))


@auth.trustee_view
@auth.requires_election_features('trustee_can_access_election')
@require_http_methods(["GET"])
def home(request, election, trustee):
    context = {
        'election': election,
        'trustee': trustee
    }
    if not trustee.public_key:
        url = election_reverse(election, 'trustee_keygen')
        return HttpResponseRedirect(url)

    set_menu('trustee', context)
    return render_template(request, 'election_trustee_home', context)


@auth.trustee_view
@auth.requires_election_features('trustee_can_access_election')
@require_http_methods(["GET"])
def json_data(request, election, trustee):

    def get_obj_public_key(obj):
        if obj.public_key:
            public_key = {
                'g': str(obj.public_key.g),
                'p': str(obj.public_key.p),
                'q': str(obj.public_key.q),
                'y': str(obj.public_key.y),
            }
        else:
            public_key = {}
        return public_key
    
    def date_to_string(date):
        if date:
            str_date = date.isoformat()
        else:
            str_date = None
        return str_date

    admins = election.admins.all()
    admins_data = []
    for admin in admins:
        data = {
            'id': admin.id,
            'user_id': admin.user_id,
            'name': admin.name,
        }
        admins_data.append(data)

    trustees = election.trustees.all()
    trustees_data = []
    for trustee in trustees:
        data = {
            'name': trustee.name,
            'public_key': get_obj_public_key(trustee),
            'email': trustee.email,
        }
        trustees_data.append(data)

    polls = election.polls.all()
    polls_data = []
    for poll in polls:
        voters = poll.voters.all()
        nr_voters = voters.count()
        nr_excluded = voters.excluded().count()
        data = {
            'uuid': poll.uuid,
            'name': poll.name,
            'short name': poll.short_name,
            'nr_voters': nr_voters,
            'nr_excluded': nr_excluded,
            'cast_votes': poll.cast_votes_count,
            'link_id': poll.link_id,
            'index': poll.index if poll.link_id else None,
            'frozen_at': date_to_string(poll.frozen_at),
            'created_at': date_to_string(poll.created_at),
            'modified_at': date_to_string(poll.modified_at),
            'questions': poll.questions,
            'questions_data': poll.questions_data,
            'voters_last_modified': date_to_string(poll.voters_last_notified_at),
        }

        include_tally = request.GET.get('include_tally')
        if not poll.encrypted_tally:
            data['encrypted_tally'] = None
        else:
            if include_tally:
                data['encrypted_tally'] = poll.encrypted_tally.toJSONDict()
            else:
                data['encrypted_tally'] = 'tally_excluded' 
        polls_data.append(data)

    data = {
        'election':
            {
            'uuid': election.uuid,
            'name': election.name,
            'short name': election.short_name,
            'description': election.description,
            'institution': election.institution.name,
            'admins': admins_data,
            'trustees': trustees_data,
            'public_key': get_obj_public_key(election),
            'help_email': election.help_email,
            'help_phone': election.help_phone,
            'starts_at': date_to_string(election.voting_starts_at),
            'ends_at': date_to_string(election.voting_ends_at),
            'extended_until': date_to_string(election.voting_extended_until),
            'polls': polls_data,
        }
    }
    json_data = json.dumps(data)
    return HttpResponse(json_data, mimetype="application/json")
