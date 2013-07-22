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

from helios.view_utils import render_template
from helios.models import Election, Trustee
from heliosauth import utils
from helios.crypto import algs

logger = logging.getLogger()


@auth.election_view(check_access=False)
@auth.unauthenticated_user_required
@auth.requires_election_features('trustee_can_login')
def login(request, election, trustee_email, trustee_secret):
    trustee = election.trustees.get(email=trustee_email)
    if not trustee:
        raise PermissionDenied("Invalid election")

    if trustee_secret == trustee.secret:
        user = auth.ZeusUser(trustee)
        user.authenticate(request)
        return HttpResponseRedirect(reverse('election_trustee_home',
                                            args=[election.uuid]))
    raise PermissionDenied


@auth.trustee_view
@auth.requires_election_features('trustee_can_generate_key')
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
def check_sk(request, election, trustee):
    context = {
        'election': election,
        'trustee': trustee
    }
    return render_template(request, 'election_trustee_check_sk', context)


@auth.trustee_view
@auth.requires_election_features('trustee_can_check_sk')
def verify_key(request, election, trustee):
    context = {
        'election': election,
        'trustee': trustee
    }
    trustee.last_verified_key_at = datetime.datetime.now()
    trustee.save()
    return render_template(request, 'election_trustee_check_sk', context)


@auth.trustee_view
@transaction.commit_on_success
@auth.requires_election_features('trustee_can_upload_pk')
def upload_pk(request, election, trustee):
    #TODO: CSRF
    if request.method == "POST":
        try:
            public_key_and_proof = \
                    utils.from_json(request.POST['public_key_json'])
            public_key = algs.EGPublicKey.fromJSONDict(
                public_key_and_proof['public_key'])
            pok = algs.DLogProof.fromJSONDict(public_key_and_proof['pok'])
            election.add_trustee_pk(trustee, public_key, pok)
        except Exception, e:
            logger.exception(e)
            transaction.rollback()
            messages.error(request, "Cannot upload public key")

    return HttpResponseRedirect(reverse('election_trustee_home',
                                        args=[election.uuid]))


@auth.trustee_view
@auth.requires_election_features('trustee_can_access_election')
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
