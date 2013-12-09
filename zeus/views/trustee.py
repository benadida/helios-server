import simplejson
import logging
import datetime

from django.conf.urls.defaults import *
from django.core.urlresolvers import reverse
from django.contrib import messages

from zeus.forms import ElectionForm
from zeus import auth
from zeus.utils import *
from zeus.views.utils import *
from zeus.views.common import *

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.views.decorators.http import require_http_methods

from helios.view_utils import render_template
from helios.models import Election, Trustee
from heliosauth import utils
from helios.crypto import algs

logger = logging.getLogger()


@auth.election_view(check_access=False)
@auth.unauthenticated_user_required
@auth.requires_election_features('trustee_can_login')
@require_http_methods(['GET'])
def login(request, election, trustee_email, trustee_secret):
    trustee = get_object_or_404(Trustee, election=election,
                                email=trustee_email)
    if not trustee:
        raise PermissionDenied("Invalid election")

    if trustee_secret == trustee.secret:
        user = auth.ZeusUser(trustee)
        user.authenticate(request)
        election.logger.info("Trustee %r logged in", trustee.email)
        return HttpResponseRedirect(reverse('election_trustee_home',
                                            args=[election.uuid]))
    raise PermissionDenied


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
