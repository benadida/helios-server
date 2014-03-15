# -*- coding: utf-8 -*-
"""
Helios Django Views

Ben Adida (ben@adida.net)
"""

from django.core.urlresolvers import reverse
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.http import *
from django.db import transaction

from mimetypes import guess_type

import csv
import urllib
import os
import base64

from crypto import algs, electionalgs, elgamal
from crypto import utils as cryptoutils
from workflows import homomorphic
from helios import utils as helios_utils
from view_utils import *

from helios_auth.security import *
from helios_auth.auth_systems import AUTH_SYSTEMS, can_list_categories
from helios_auth.models import AuthenticationExpired

from helios import security
from helios_auth import views as auth_views

import tasks

from security import *
from helios_auth.security import get_user, save_in_session_across_logouts

import uuid
import datetime

from models import *

import forms
import signals
from bulletin_board import thresholdalgs
from bulletin_board.models import Signed_Encrypted_Share, Ei, Incorrect_share, Signature
from helios.constants import p, g, q, ground_1, ground_2

# parameters for everything
ELGAMAL_PARAMS = elgamal.Cryptosystem()

# trying new ones from OlivierP
ELGAMAL_PARAMS.p = p
ELGAMAL_PARAMS.q = q

ELGAMAL_PARAMS.g = g

# object ready for serialization
ELGAMAL_PARAMS_LD_OBJECT = datatypes.LDObject.instantiate(
    ELGAMAL_PARAMS, datatype='legacy/EGParams')


##
# helper functions
##


def get_election_url(election):
    return settings.URL_HOST + reverse(election_shortcut, args=[election.short_name])


def get_election_badge_url(election):
    return settings.URL_HOST + reverse(election_badge, args=[election.uuid])


def get_election_govote_url(election):
    return settings.URL_HOST + reverse(election_vote_shortcut, args=[election.short_name])


def get_castvote_url(cast_vote):
    return settings.URL_HOST + reverse(castvote_shortcut, args=[cast_vote.vote_tinyhash])


##
# social buttons
##


def get_socialbuttons_url(url, text):
    if not text:
        return None

    return "%s%s?%s" % (settings.SOCIALBUTTONS_URL_HOST,
                        reverse(socialbuttons),
                        urllib.urlencode({
                            'url': url,
                            'text': text.encode('utf-8')
                        }))


##
# remote helios_auth utils
##


def user_reauth(request, user):
    # FIXME: should we be wary of infinite redirects here, and
    # add a parameter to prevent it? Maybe.
    login_url = "%s%s?%s" % (settings.SECURE_URL_HOST,
                             reverse(auth_views.start, args=[user.user_type]),
                             urllib.urlencode({'return_url':
                                               request.get_full_path()}))
    return HttpResponseRedirect(login_url)

##
# simple admin for development
##


def admin_autologin(request):
    if "localhost" not in settings.URL_HOST and "127.0.0.1" not in settings.URL_HOST:
        raise Http404

    users = User.objects.filter(admin_p=True)
    if len(users) == 0:
        return HttpResponse("no admin users!")

    if len(users) == 0:
        return HttpResponse("no users!")

    user = users[0]
    request.session['user'] = {'type': user.user_type, 'user_id': user.user_id}
    return HttpResponseRedirect("/")

##
# general election features
##


@json
def election_params(request):
    return ELGAMAL_PARAMS_LD_OBJECT.toJSONDict()


def election_verifier(request):
    return render_template(request, "tally_verifier")


def election_single_ballot_verifier(request):
    return render_template(request, "ballot_verifier")


def election_shortcut(request, election_short_name):
    election = Election.get_by_short_name(election_short_name)
    if election:
        return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))
    else:
        raise Http404


@election_view()
def _election_vote_shortcut(request, election):
    """
    a hidden view behind the shortcut that performs the actual perm check
    """
    vote_url = "%s/booth/vote.html?%s" % (settings.SECURE_URL_HOST, urllib.urlencode(
        {'election_url': reverse(one_election, args=[election.uuid])}))

    test_cookie_url = "%s?%s" % (
        reverse(test_cookie), urllib.urlencode({'continue_url': vote_url}))

    return HttpResponseRedirect(test_cookie_url)


def election_vote_shortcut(request, election_short_name):
    election = Election.get_by_short_name(election_short_name)
    if election:
        return _election_vote_shortcut(request, election_uuid=election.uuid)
    else:
        raise Http404


@election_view()
def _castvote_shortcut_by_election(request, election, cast_vote):
    return render_template(request, 'castvote', {'cast_vote': cast_vote, 'vote_content': cast_vote.vote.toJSON(), 'the_voter': cast_vote.voter, 'election': election})


def castvote_shortcut(request, vote_tinyhash):
    try:
        cast_vote = CastVote.objects.get(vote_tinyhash=vote_tinyhash)
    except CastVote.DoesNotExist:
        raise Http404

    return _castvote_shortcut_by_election(request, election_uuid=cast_vote.voter.election.uuid, cast_vote=cast_vote)


@login_required
def elections_administered(request):
    if not can_create_election(request):
        return HttpResponseForbidden('only an administrator has elections to administer')

    user = get_user(request)
    elections = Election.get_by_user_as_admin(user)

    return render_template(request, "elections_administered", {'elections': elections})


@login_required
def elections_voted(request):
    user = get_user(request)
    elections = Election.get_by_user_as_voter(user)

    return render_template(request, "elections_voted", {'elections': elections})


@login_required
def election_new(request):
    if not can_create_election(request):
        return HttpResponseForbidden('Only an administrator can create an election')

    error = None

    if request.method == "GET":
        election_form = forms.ElectionForm(
            initial={'private_p': settings.HELIOS_PRIVATE_DEFAULT})
    else:
        election_form = forms.ElectionForm(request.POST)

        if election_form.is_valid():
            # create the election obj
            election_params = dict(election_form.cleaned_data)

            # is the short name valid
            if helios_utils.urlencode(election_params['short_name']) == election_params['short_name']:
                election_params['uuid'] = str(uuid.uuid1())
                election_params['cast_url'] = settings.SECURE_URL_HOST + \
                    reverse(one_election_cast, args=[election_params['uuid']])

                # registration starts closed
                election_params['openreg'] = False

                user = get_user(request)
                election_params['admin'] = user

                election, created_p = Election.get_or_create(**election_params)

                if created_p:
                    # add Helios as a trustee by default
                    election.generate_trustee(ELGAMAL_PARAMS)

                    return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))
                else:
                    error = "An election with short name %s already exists" % election_params[
                        'short_name']
            else:
                error = "No special characters allowed in the short name."

    return render_template(request, "election_new", {'election_form': election_form, 'error': error})


@election_admin(frozen=False)
def one_election_edit(request, election):
    error = None
    RELEVANT_FIELDS = ['short_name', 'name', 'description', 'use_voter_aliases',
                       'election_type', 'randomize_answer_order', 'private_p', 'use_threshold', 'help_email']
    # RELEVANT_FIELDS += ['use_advanced_audit_features']

    if settings.ALLOW_ELECTION_INFO_URL:
        RELEVANT_FIELDS += ['election_info_url']

    if request.method == "GET":
        values = {}
        for attr_name in RELEVANT_FIELDS:
            values[attr_name] = getattr(election, attr_name)
        election_form = forms.ElectionForm(values)
    else:
        election_form = forms.ElectionForm(request.POST)

        if election_form.is_valid():
            clean_data = election_form.cleaned_data
            for attr_name in RELEVANT_FIELDS:
                setattr(election, attr_name, clean_data[attr_name])

            election.save()

            return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))

    return render_template(request, "election_edit", {'election_form': election_form, 'election': election, 'error': error})


@election_admin(frozen=False)
def one_election_schedule(request, election):
    return HttpResponse("foo")


@election_view()
@json
def one_election(request, election):
    if not election:
        raise Http404
    return election.toJSONDict(complete=True)


@election_view()
@json
def one_election_meta(request, election):
    if not election:
        raise Http404
    return election.metadata


@election_view()
def election_badge(request, election):
    election_url = get_election_url(election)
    params = {'election': election, 'election_url': election_url}
    for option_name in ['show_title', 'show_vote_link']:
        params[option_name] = (request.GET.get(option_name, '1') == '1')
    return render_template(request, "election_badge", params)


@election_view()
def one_election_view(request, election):
    user = get_user(request)
    admin_p = security.user_can_admin_election(user, election)
    can_feature_p = security.user_can_feature_election(user, election)

    notregistered = False
    eligible_p = True

    election_url = get_election_url(election)
    election_badge_url = get_election_badge_url(election)
    status_update_message = None

    vote_url = "%s/booth/vote.html?%s" % (settings.SECURE_URL_HOST, urllib.urlencode(
        {'election_url': reverse(one_election, args=[election.uuid])}))

    test_cookie_url = "%s?%s" % (
        reverse(test_cookie), urllib.urlencode({'continue_url': vote_url}))

    if user:
        voter = Voter.get_by_election_and_user(election, user)

        if not voter:
            try:
                eligible_p = _check_eligibility(election, user)
            except AuthenticationExpired:
                return user_reauth(request, user)
            notregistered = True
    else:
        voter = get_voter(request, user, election)

    if voter:
        # cast any votes?
        votes = CastVote.get_by_voter(voter)
    else:
        votes = None

    # status update message?
    if election.openreg:
        if election.voting_has_started:
            status_update_message = u"Vote in %s" % election.name
        else:
            status_update_message = u"Register to vote in %s" % election.name

    # result!
    if election.result:
        status_update_message = u"Results are in for %s" % election.name

    # a URL for the social buttons
    socialbuttons_url = get_socialbuttons_url(
        election_url, status_update_message)

    trustees = Trustee.get_by_election(election)
    if(election.questions):
        question_numbers = range(len(election.questions))
    else:
        question_numbers = []
    return render_template(request, 'election_view',
                           {'election': election, 'trustees': trustees, 'admin_p': admin_p, 'user': user,
                            'voter': voter, 'votes': votes, 'notregistered': notregistered, 'eligible_p': eligible_p,
                            'can_feature_p': can_feature_p, 'election_url': election_url,
                            'vote_url': vote_url, 'election_badge_url': election_badge_url,
                            'test_cookie_url': test_cookie_url, 'socialbuttons_url': socialbuttons_url, 'question_numbers': question_numbers})


def test_cookie(request):
    continue_url = request.GET['continue_url']
    request.session.set_test_cookie()
    next_url = "%s?%s" % (
        reverse(test_cookie_2), urllib.urlencode({'continue_url': continue_url}))
    return HttpResponseRedirect(settings.SECURE_URL_HOST + next_url)


def test_cookie_2(request):
    continue_url = request.GET['continue_url']

    if not request.session.test_cookie_worked():
        return HttpResponseRedirect(settings.SECURE_URL_HOST + ("%s?%s" % (reverse(nocookies), urllib.urlencode({'continue_url': continue_url}))))

    request.session.delete_test_cookie()
    return HttpResponseRedirect(continue_url)


def nocookies(request):
    retest_url = "%s?%s" % (reverse(test_cookie), urllib.urlencode(
        {'continue_url': request.GET['continue_url']}))
    return render_template(request, 'nocookies', {'retest_url': retest_url})


def socialbuttons(request):
    """
    just render the social buttons for sharing a URL
    expecting "url" and "text" in request.GET
    """
    return render_template(request, 'socialbuttons',
                           {'url': request.GET['url'], 'text': request.GET['text']})


##
# Trustees and Public Key
# As of July 2009, there are always trustees for a Helios election: one trustee is acceptable, for simple elections.
##

@election_admin(frozen=None)
@json
def trustees_list(request, election):
    trustees = Trustee.get_by_election(election)
    return [t.toJSONDict(complete=True) for t in trustees]


@election_admin(frozen=None)
def trustees_list_view(request, election):
    trustees = Trustee.get_by_election(election)
    user = get_user(request)
    admin_p = security.user_can_admin_election(user, election)
    election_id = election.id
    signed_encrypted_shares = Signed_Encrypted_Share.objects.filter(
        election_id=election_id)
    scheme = None
    if (election.use_threshold):
        if (election.frozen_trustee_list):
            scheme = election.get_scheme()
            if scheme:
                n = scheme.n
                if len(signed_encrypted_shares) == n * n:
                    election.encrypted_shares_uploaded = True
                else:
                    election.encrypted_shares_uploaded = False
            else:
                election.encrypted_shares_uploaded = False

            election.save()

        if election.has_helios_trustee():
            helios_trustee = election.get_helios_trustee()
            if ((helios_trustee.public_key == None)and(helios_trustee.secret_key == None)and(election.encrypted_shares_uploaded)):
                # calculate helios key
                helios_key = Key.objects.get(id=helios_trustee.key_id)
                helios_secret_key_string = SecretKey.objects.get(
                    public_key=helios_key).secret_key_encrypt
                helios_secret_key = elgamal.SecretKey.from_dict(
                    utils.from_json(helios_secret_key_string))
                receiver_id = helios_key.id
                election_id = election.id
                scheme = Thresholdscheme.objects.get(election=election)
                n = scheme.n
                k = scheme.k

                # write data_receiver
                signed_encrypted_shares_strings = Signed_Encrypted_Share.objects.filter(
                    receiver_id=receiver_id).filter(election_id=election_id).order_by('signer_id')
                signed_encrypted_shares = []
                receiver_ids = []
                signer_ids = []
                for share in signed_encrypted_shares_strings:
                    signed_encrypted_shares.append(
                        thresholdalgs.Signed_Encrypted_Share.from_dict(utils.from_json(share.share)))
                    receiver_ids.append(share.receiver_id)
                    signer_ids.append(share.signer_id)
                correct_secret_shares = []
                if(len(signed_encrypted_shares) == n):
                    for j in range(len(signed_encrypted_shares)):
                        element = signed_encrypted_shares[j]
                        receiver_id_share = receiver_ids[j]
                        signer_id_share = signer_ids[j]
                        pk_signer_signing = elgamal.PublicKey.from_dict(
                            utils.from_json(Key.objects.get(id=signer_id_share).public_key_signing))

                        encry_share = element.encr_share
                        sig = element.sig
                        share = encry_share.decrypt(helios_secret_key)
                        share_string = utils.to_json_js(share.to_dict())

                        correct_share = False
                        if sig.verify(share_string, pk_signer_signing, p, q, g):
                            if share.verify_share(scheme, p, q, g):
                                correct_secret_shares.append(share)
                                correct_share = True
                            else:
                                share_string = utils.to_json(share.to_dict())
                                incorrect_share = Incorrect_share(
                                    share_string, election_id, sig, signer_id, receiver_id, 'invalid commitments')
                                incorrect_share.save()
                        else:
                            share_string = utils.to_json(share.to_dict())
                            incorrect_share = Incorrect_share()
                            incorrect_share.share = share_string
                            incorrect_share.election_id = election_id
                            incorrect_share.sig = sig

                            incorrect_share.signer_id = signer_id_share
                            incorrect_share.receiver_id = receiver_id_share
                            incorrect_share.explanation = 'invalid signature'
                            incorrect_share.save()

                if len(correct_secret_shares) == n:
                    s_value = 0
                    t_value = 0
                    share = correct_secret_shares[0]
                    for i in range(1, len(correct_secret_shares)):
                        share.add(correct_secret_shares[i], p, q, g)

                    if share.verify_share(scheme, p, q, g):
                        final_public_key = elgamal.PublicKey()
                        final_public_key.q = q
                        final_public_key.g = g
                        final_public_key.p = p
                        final_public_key.y = pow(g, share.point_s.y_value, p)
                        final_secret_key = elgamal.SecretKey()
                        final_secret_key.public_key = final_public_key
                        final_secret_key.x = share.point_s.y_value

                        helios_trustee.public_key = final_public_key
                        helios_trustee.secret_key = final_secret_key
                        helios_trustee.public_key_hash = datatypes.LDObject.instantiate(
                            helios_trustee.public_key, datatype='legacy/EGPublicKey').hash
                        helios_trustee.pok = helios_trustee.secret_key.prove_sk(
                            algs.DLog_challenge_generator)
                        helios_trustee.save()

    return render_template(request, 'trustees_list', {'election': election, 'trustees': trustees, 'admin_p': admin_p, 'scheme': scheme})


@election_admin(frozen=False)
def trustees_create(request, election):
    if not (election.frozen_trustee_list):
        if request.method == "GET":
            return render_template(request, 'trustees_create', {'election': election})
        else:
            # get the public key and the hash, and add it
            name = request.POST['name']
            email = request.POST['email']

            trustee = Trustee(
                uuid=str(uuid.uuid1()), election=election, name=name, email=email)
            trustee.save()
            return HttpResponseRedirect(reverse(trustees_list_view, args=[election.uuid]))
    else:
        return HttpResponseRedirect(reverse(trustees_list_view, args=[election.uuid]))


@election_admin(frozen=False)
def trustees_create_helios(request, election):
    """
    make Helios a trustee of the election
    """
    if not (election.frozen_trustee_list):
        election.generate_trustee(ELGAMAL_PARAMS)
    return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(trustees_list_view, args=[election.uuid]))


@election_admin(frozen=False)
def trustees_delete(request, election):
    if not (election.frozen_trustee_list):
        trustee = Trustee.get_by_election_and_uuid(
            election, request.GET['uuid'])
        trustee.delete()
    return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(trustees_list_view, args=[election.uuid]))

@election_admin(frozen=False)
def trustees_freeze(request, election):
    if request.method == 'POST':
        form = forms.ThresholdSchemeForm(request.POST)
        if form.is_valid():
            # process the data in form.cleaned_data
            trustees = Trustee.objects.filter(election=election)
            scheme = Thresholdscheme()
            scheme.election = election
            scheme.n = len(trustees)
            scheme.ground_1 = ground_1
            scheme.ground_2 = ground_2
            scheme.k = form.cleaned_data['k']
            scheme.save()
            election.frozen_trustee_list = True

            if election.has_helios_trustee():
                if scheme.n == 1:
                    helios_trustee = election.get_helios_trustee()
                    key = helios_trustee.key
                    sk = SecretKey.objects.filter(public_key=key)[0]
                    sk_signature = sk.secret_key_signing
                    add_encrypted_shares(request, election, sk_signature)
                    election.encrypted_shares_uploaded = True

            election.save()

            return HttpResponseRedirect(reverse(trustees_list_view, args=[election.uuid]))

    else:
        trustees = Trustee.objects.filter(election=election)
        n = len(trustees)
        return render_template(request, 'trustees_freeze', {'election': election, 'n': n})


def add_encrypted_shares(request, election, signature=None):
    election_id = election.id
    trustees = Trustee.objects.filter(election=election).order_by('id')
    scheme = Thresholdscheme.objects.filter(election=election)[0]
    n = scheme.n
    pk_list = []
    for i in range(len(trustees)):
        pk_list.append(trustees[i].key)

    if len(pk_list) != n:
        return Exception('The number of public keys for communication must equal: ' + str(n))

    # if the form has been submitted...
    if (signature) or (request.method == 'POST'):
        if (signature == None):
            form = forms.SignatureForm(request.POST)

        if (signature) or (form.is_valid()):
            if (signature == None):
                instances = form.save(commit=False)
                signature = instances.signature
            secret_key_sig = algs.EGSecretKey.from_dict(
                utils.from_json(signature))
            for j in range(len(pk_list)):
                pk = pk_list[j]
                if (pow(g, secret_key_sig.x, p) == elgamal.PublicKey.from_dict(utils.from_json(pk.public_key_signing)).y):
                    signer = pk.name
                    signer_id = pk.id
                    trustee_signer_id = trustees[j].id
                    break

            if not signer:
                return HttpResponse('Your signature does not belong to the election: ' + election.name)

            if (len(Signed_Encrypted_Share.objects.filter(signer_id=signer_id).filter(election_id=election.id)) > 0):
                return render_template(request, 'shares_already_uploaded', {'signer': signer, 'election': election})

            s = algs.Utils.random_mpz_lt(q)
            t = algs.Utils.random_mpz_lt(q)

            shares = scheme.share_verifiably(s, t, ELGAMAL_PARAMS)

            if len(pk_list) == len(shares):
                for i in range(len(trustees)):
                    trustee_temp = trustees[i]
                    key = trustee_temp.key
                    receiver = key.name
                    receiver_id = key.id

                    share = shares[i]
                    share_string = cryptoutils.to_json_js(share.to_dict())
                    if(share.point_s.x_value != trustee_temp.id):
                        return Exception('Shares have wrong x_coordinate')

                    encry_share = share.encrypt(
                        algs.EGPublicKey.from_dict(utils.from_json(key.public_key_encrypt)))
                    sig = share.sign(secret_key_sig, p, q, g)
                    signed_encry_share = thresholdalgs.Signed_Encrypted_Share(
                        sig, encry_share)

                    encry_share = Signed_Encrypted_Share()
                    encry_share.share = utils.to_json(
                        signed_encry_share.to_dict())
                    pk_sign = Key.objects.filter(id=signer_id)[0]
                    if(sig.verify(share_string, algs.EGPublicKey.from_dict(utils.from_json(pk_sign.public_key_signing)), p, q, g)):
                        encry_share.signer = pk_sign.name
                        encry_share.signer_id = signer_id
                        encry_share.receiver = receiver
                        encry_share.receiver_id = receiver_id
                        encry_share.election_id = election_id
                        encry_share.trustee_receiver_id = trustees[i].id
                        encry_share.trustee_signer_id = trustee_signer_id
                        encry_share.save()

                    else:
                        return Exception('Wrong signature')

                    if (len(Signed_Encrypted_Share.objects.filter(signer_id=signer_id).filter(election_id=election_id)) == scheme.n):
                        signer_key = Key.objects.get(id=signer_id)
                        signer_trustee = Trustee.objects.filter(
                            key=signer_key)[0]
                        signer_trustee.added_encrypted_shares = True
                        signer_trustee.save()
                return HttpResponseRedirect('/bulletin_board/elections/' + str(election_id) + '/')
            else:
                return Exception('pk_list and shares do not have the same length')

            return render_template()

    else:
        form = SignatureForm()

    return render_template(request, 'signature_form', {'election': election})


def trustee_login(request, election_short_name, trustee_email, trustee_secret):
    election = Election.get_by_short_name(election_short_name)
    if election:
        trustee = Trustee.get_by_election_and_email(election, trustee_email)

        if trustee:
            if trustee.secret == trustee_secret:
                set_logged_in_trustee(request, trustee)
                return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(trustee_home, args=[election.uuid, trustee.uuid]))
            else:
                # bad secret, we'll let that redirect to the front page
                pass
        else:
            # no such trustee
            raise Http404

    return HttpResponseRedirect(settings.SECURE_URL_HOST + "/")


@election_admin()
def trustee_send_url(request, election, trustee_uuid):
    trustee = Trustee.get_by_election_and_uuid(election, trustee_uuid)

    url = settings.SECURE_URL_HOST + \
        reverse(
            trustee_login, args=[election.short_name, trustee.email, trustee.secret])

    body = """

You are a trustee for %s.

Your trustee dashboard is at

  %s
  
--
Helios  
""" % (election.name, url)

    send_mail('Trustee Dashboard for %s' % election.name, body, settings.SERVER_EMAIL, [
              "%s <%s>" % (trustee.name, trustee.email)], fail_silently=True)

    logging.info("URL %s " % url)
    return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(trustees_list_view, args=[election.uuid]))


@trustee_check
def trustee_home(request, election, trustee):
    if not (election.use_threshold) or not (trustee.key):
        return render_template(request, 'trustee_home', {'election': election, 'trustee': trustee})

    election_id = election.id
    try:
        scheme = Thresholdscheme.objects.get(election=election)
    except Thresholdscheme.DoesNotExist:
        scheme = None

    signer_id = trustee.key.id
    trustees = Trustee.objects.filter(election=election).order_by('id')

    scheme_params_json = None
    if (scheme):
        SCHEME_PARAMS_LD_OBJECT = datatypes.LDObject.instantiate(
            scheme, datatype='legacy/Thresholdscheme')
        scheme_params_json = utils.to_json(SCHEME_PARAMS_LD_OBJECT.toJSONDict())

    # Create dictionary with all public_keys
    eg_params_json = utils.to_json(ELGAMAL_PARAMS_LD_OBJECT.toJSONDict())
    pk_encrypt_dict = {}
    pk_signing_dict = {}
    name_dict = {}
    id_dict = {}
    trustee_ids_dict = {}
    email_dict = {}
    pok_encrypt_dict = {}
    pok_signing_dict = {}
    pk_encrypt_hash_dict = {}
    pk_signing_hash_dict = {}
    for i in range(len(trustees)):
        key = Key.objects.get(id=trustees[i].key_id)
        id_dict[str(i)] = key.id
        corresponding_trustee = Trustee.objects.filter(key=key)[0]
        trustee_ids_dict[str(i)] = corresponding_trustee.id
        name_dict[str(i)] = key.name
        email_dict[str(i)] = key.email
        pok_encrypt_dict[str(i)] = key.pok_encrypt
        pok_signing_dict[str(i)] = key.pok_signing
        pk_encrypt_hash_dict[str(i)] = key.public_key_encrypt_hash
        pk_signing_hash_dict[str(i)] = key.public_key_signing_hash
        pk_encrypt_dict[str(i)] = key.public_key_encrypt
        pk_signing_dict[str(i)] = key.public_key_signing

    # pass encrypted shares if there are any
    encry_shares = Signed_Encrypted_Share.objects.filter(election_id=election_id).filter(
        receiver_id=trustee.key.id).order_by('trustee_signer_id')
    encry_shares_dict = {}
    if(encry_shares):
        for i in range(len(encry_shares)):
            item = encry_shares[i]
            encry_share = thresholdalgs.Signed_Encrypted_Share.from_dict(
                utils.from_json(item.share))

            encry_shares_dict[str(i)] = utils.to_json(encry_share.to_dict())

    return render_template(request, 'trustee_home', {"election_id": election_id, "trustee": trustee, "signer_id": signer_id, "election": election, "trustees": trustees, "trustee_ids_dict": trustee_ids_dict,
                                                     "scheme_params_json": scheme_params_json, "id_dict": id_dict, "name_dict": utils.to_json(name_dict), "email_dict": utils.to_json(email_dict),
                                                     "pok_encrypt_dict": utils.to_json(pok_encrypt_dict), "pok_signing_dict": utils.to_json(pok_signing_dict), "pk_encrypt_hash_dict": utils.to_json(pk_encrypt_hash_dict),
                                                     "pk_signing_hash_dict": utils.to_json(pk_signing_hash_dict), "pk_encrypt_dict": utils.to_json(pk_encrypt_dict), "pk_signing_dict": utils.to_json(pk_signing_dict),
                                                     "eg_params_json": eg_params_json, 'encry_shares_dict': encry_shares_dict})


@trustee_check
def trustee_keygenerator(request, election, trustee):
    """
    a key generator with the current params
    """
    eg_params_json = utils.to_json(ELGAMAL_PARAMS_LD_OBJECT.toJSONDict())

    return render_template(request, "trustee_keygenerator", {'eg_params_json': eg_params_json, 'election': election, 'trustee': trustee})

@trustee_check
def trustee_keygenerator_threshold(request, election, trustee):
    """
    a key generator for threshold encryption with the current params
    """
    if request.method == "POST":
        key = Key()
        key.name = trustee.name
        key.email = trustee.email

        # get the public key and the hash, and add ii
        public_key_and_proof_enc = utils.from_json(
            request.POST['public_key_json_enc'])
        public_key_enc = algs.EGPublicKey.fromJSONDict(
            public_key_and_proof_enc['public_key'])
        pok_enc = algs.DLogProof.fromJSONDict(public_key_and_proof_enc['pok'])

        # verify the proof
        if not public_key_enc.verify_sk_proof(pok_enc, algs.DLog_challenge_generator):
            raise Exception("Bad proof for public key encrypting")
        key.public_key_encrypt = utils.to_json(public_key_enc.to_dict())
        key.pok_encrypt = utils.to_json(pok_enc.to_dict())
        key.public_key_encrypt_hash = cryptoutils.hash_b64(
            key.public_key_encrypt)

        public_key_and_proof_sign = utils.from_json(
            request.POST['public_key_json_sign'])
        public_key_sign = algs.EGPublicKey.fromJSONDict(
            public_key_and_proof_sign['public_key'])
        pok_sign = algs.DLogProof.fromJSONDict(
            public_key_and_proof_sign['pok'])

        # verify the proof
        if not public_key_sign.verify_sk_proof(pok_sign, algs.DLog_challenge_generator):
            raise Exception("Bad proof for public key signing")
        key.public_key_signing = utils.to_json(public_key_sign.to_dict())
        key.pok_signing = utils.to_json(pok_sign.to_dict())
        key.public_key_signing_hash = cryptoutils.hash_b64(
            key.public_key_signing)

        key.save()

        # assign the key to the trustee
        trustee.key = key
        trustee.save()

        # send a note to admin
        try:
            election.admin.send_message(
                "pk upload, " + "%s uploaded a pk for communication." % (key.name))
        except:
            # oh well, no message sent
            pass

        return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(trustee_home, args=[election.uuid, trustee.uuid]))

    eg_params_json = utils.to_json(ELGAMAL_PARAMS_LD_OBJECT.toJSONDict())

    return render_template(request, "trustee_keygenerator_threshold", {'eg_params_json': eg_params_json, 'election': election, 'trustee': trustee})


@trustee_check
def trustee_upload_encrypted_shares(request, election, trustee):
    election_id = election.id
    signer_key = trustee.key
    signer_id = signer_key.id
    trustees = Trustee.objects.filter(election=election).order_by('id')
    scheme = Thresholdscheme.objects.get(election=election)
    signer_key = Key.objects.get(id=signer_id)
    signer_trustee = Trustee.objects.filter(key=signer_key)[0]
    n = scheme.n

    encry_shares_dict = utils.from_json(request.POST['encry_shares'])
    encry_shares = []
    for i in range(n):
        dict = encry_shares_dict[str(i)]
        item = thresholdalgs.Signed_Encrypted_Share.from_dict(dict)
        encry_shares.append(item)

    if len(encry_shares) == n:
        for i in range(n):
            receiver_id = trustees[i].key.id
            receiver = trustees[i].key.name
            encry_share_model = Signed_Encrypted_Share()
            encry_share_model.election_id = election_id
            encry_share_model.share = utils.to_json(encry_shares[i].to_dict())
            encry_share_model.signer = signer_key.name
            encry_share_model.signer_id = signer_id
            encry_share_model.receiver = receiver
            encry_share_model.receiver_id = receiver_id
            encry_share_model.trustee_signer_id = trustee.id
            encry_share_model.trustee_receiver_id = trustees[i].id
            encry_share_model.save()

    if (len(Signed_Encrypted_Share.objects.filter(election_id=election_id).filter(signer_id=signer_id)) == n):
        trustee.added_encrypted_shares = True
        trustee.save()

    if election.has_helios_trustee():
        trustees_added_encrypted_shares = True
        for trustee in trustees:
            if not trustee.added_encrypted_shares:
                done = False

        if trustees_added_encrypted_shares:
            helios_trustee = election.get_helios_trustee()
            key = helios_trustee.key
            sk = SecretKey.objects.filter(public_key=key)[0]
            sk_signature = sk.secret_key_signing
            add_encrypted_shares(request, election, sk_signature)
            election.encrypted_shares_uploaded = True
            election.save()

    try:
        # send a note to admin
        election.admin.send_message("%s - encrypted shares uploaded by " %
                                    election.name, "trustee %s (%s)" % (signer_trustee.name, signer_trustee.email))
    except:
        # oh well, no message sent
        pass

    return SUCCESS


@trustee_check
def trustee_check_sk(request, election, trustee):
    return render_template(request, 'trustee_check_sk', {'election': election, 'trustee': trustee})


@trustee_check
def trustee_upload_pk(request, election, trustee):
    if request.method == "POST":
    # get the public key and the hash, and add it
        public_key_and_proof = utils.from_json(request.POST['public_key_json'])
        trustee.public_key = algs.EGPublicKey.fromJSONDict(
            public_key_and_proof['public_key'])
        trustee.pok = algs.DLogProof.fromJSONDict(public_key_and_proof['pok'])

        # verify the pok
        if not trustee.public_key.verify_sk_proof(trustee.pok, algs.DLog_challenge_generator):
            raise Exception('Bad proof for this public key')

        trustee.public_key_hash = utils.hash_b64(
            utils.to_json(trustee.public_key.toJSONDict()))

        trustee.save()

        # send a note to admin
        try:
            election.admin.send_message(
                "%s - trustee pk upload" % election.name, "trustee %s (%s) uploaded a pk." % (trustee.name, trustee.email))
        except:
            # oh well, no message sent
            pass

    return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(trustee_home, args=[election.uuid, trustee.uuid]))


##
# Ballot Management
##


@json
def get_randomness(request):
    """
    get some randomness to sprinkle into the SJCL entropy pool
    """
    return {
        # back to urandom, it's fine
        "randomness": base64.b64encode(os.urandom(32))
        #"randomness" : base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes)
    }


@election_view(frozen=True)
@json
def encrypt_ballot(request, election):
    """
    perform the ballot encryption given answers_json, a JSON'ified list of list of answers
    list of list because each question could have a list of answers if more than one
    """
    # FIXME: maybe make this just request.POST at some point?
    answers = utils.from_json(request.REQUEST['answers_json'])
    ev = homomorphic.EncryptedVote.fromElectionAndAnswers(election, answers)
    return ev.ld_object.includeRandomness().toJSONDict()


@election_view(frozen=True)
def post_audited_ballot(request, election):
    if request.method == "POST":
        raw_vote = request.POST['audited_ballot']
        encrypted_vote = electionalgs.EncryptedVote.fromJSONDict(
            utils.from_json(raw_vote))
        vote_hash = encrypted_vote.get_hash()
        audited_ballot = AuditedBallot(
            raw_vote=raw_vote, vote_hash=vote_hash, election=election)
        audited_ballot.save()

        return SUCCESS


# we don't require frozen election to allow for ballot preview
@election_view()
def one_election_cast(request, election):
    """
    on a GET, this is a cancellation, on a POST it's a cast
    """
    if request.method == "GET":
        return HttpResponseRedirect("%s%s" % (settings.SECURE_URL_HOST, reverse(one_election_view, args=[election.uuid])))

    user = get_user(request)
    encrypted_vote = request.POST['encrypted_vote']

    save_in_session_across_logouts(request, 'encrypted_vote', encrypted_vote)

    return HttpResponseRedirect("%s%s" % (settings.SECURE_URL_HOST, reverse(one_election_cast_confirm, args=[election.uuid])))


@election_view(allow_logins=True)
def password_voter_login(request, election):
    """
    This is used to log in as a voter for a particular election
    """

    # the URL to send the user to after they've logged in
    return_url = request.REQUEST.get(
        'return_url', reverse(one_election_cast_confirm, args=[election.uuid]))
    bad_voter_login = (request.GET.get('bad_voter_login', "0") == "1")

    if request.method == "GET":
        # if user logged in somehow in the interim, e.g. using the login link for administration,
        # then go!
        if user_can_see_election(request, election):
            return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))

        password_login_form = forms.VoterPasswordForm()
        return render_template(request, 'password_voter_login',
                               {'election': election,
                                'return_url': return_url,
                                'password_login_form': password_login_form,
                                'bad_voter_login': bad_voter_login})

    login_url = request.REQUEST.get('login_url', None)

    if not login_url:
        # login depending on whether this is a private election
        # cause if it's private the login is happening on the front page
        if election.private_p:
            login_url = reverse(password_voter_login, args=[election.uuid])
        else:
            login_url = reverse(
                one_election_cast_confirm, args=[election.uuid])

    password_login_form = forms.VoterPasswordForm(request.POST)

    if password_login_form.is_valid():
        try:
            voter = election.voter_set.get(voter_login_id=password_login_form.cleaned_data['voter_id'].strip(),
                                           voter_password=password_login_form.cleaned_data['password'].strip())

            request.session['CURRENT_VOTER'] = voter

            # if we're asked to cast, let's do it
            if request.POST.get('cast_ballot') == "1":
                return one_election_cast_confirm(request, election.uuid)

        except Voter.DoesNotExist:
            redirect_url = login_url + "?" + urllib.urlencode({
                'bad_voter_login': '1',
                'return_url': return_url
            })

            return HttpResponseRedirect(settings.SECURE_URL_HOST + redirect_url)

    return HttpResponseRedirect(settings.SECURE_URL_HOST + return_url)


@election_view()
def one_election_cast_confirm(request, election):
    user = get_user(request)

    # if no encrypted vote, the user is reloading this page or otherwise
    # getting here in a bad way
    if not request.session.has_key('encrypted_vote'):
        return HttpResponseRedirect(settings.URL_HOST)

    # election not frozen or started
    if not election.voting_has_started():
        return render_template(request, 'election_not_started', {'election': election})

    voter = get_voter(request, user, election)

    # auto-register this person if the election is openreg
    if user and not voter and election.openreg:
        voter = _register_voter(election, user)

    # tallied election, no vote casting
    if election.encrypted_tally or election.result:
        return render_template(request, 'election_tallied', {'election': election})

    encrypted_vote = request.session['encrypted_vote']
    vote_fingerprint = cryptoutils.hash_b64(encrypted_vote)

    # if this user is a voter, prepare some stuff
    if voter:
        vote = datatypes.LDObject.fromDict(
            utils.from_json(encrypted_vote), type_hint='legacy/EncryptedVote').wrapped_obj

        # prepare the vote to cast
        cast_vote_params = {
            'vote': vote,
            'voter': voter,
            'vote_hash': vote_fingerprint,
            'cast_at': datetime.datetime.utcnow()
        }

        cast_vote = CastVote(**cast_vote_params)
    else:
        cast_vote = None

    if request.method == "GET":
        if voter:
            past_votes = CastVote.get_by_voter(voter)
            if len(past_votes) == 0:
                past_votes = None
        else:
            past_votes = None

        if cast_vote:
            # check for issues
            issues = cast_vote.issues(election)
        else:
            issues = None

        bad_voter_login = (request.GET.get('bad_voter_login', "0") == "1")

        # status update this vote
        if voter and voter.user.can_update_status():
            status_update_label = voter.user.update_status_template(
            ) % "your smart ballot tracker"
            status_update_message = "I voted in %s - my smart tracker is %s.. #heliosvoting" % (
                get_election_url(election), cast_vote.vote_hash[:10])
        else:
            status_update_label = None
            status_update_message = None

        # do we need to constrain the auth_systems?
        if election.eligibility:
            auth_systems = [e['auth_system'] for e in election.eligibility]
        else:
            auth_systems = None

        password_only = False

        if auth_systems == None or 'password' in auth_systems:
            show_password = True
            password_login_form = forms.VoterPasswordForm()

            if auth_systems == ['password']:
                password_only = True
        else:
            show_password = False
            password_login_form = None

        return_url = reverse(one_election_cast_confirm, args=[election.uuid])
        login_box = auth_views.login_box_raw(
            request, return_url=return_url, auth_systems=auth_systems)

        return render_template(request, 'election_cast_confirm', {
            'login_box': login_box, 'election': election, 'vote_fingerprint': vote_fingerprint,
            'past_votes': past_votes, 'issues': issues, 'voter': voter,
            'return_url': return_url,
            'status_update_label': status_update_label, 'status_update_message': status_update_message,
            'show_password': show_password, 'password_only': password_only, 'password_login_form': password_login_form,
            'bad_voter_login': bad_voter_login})

    if request.method == "POST":
        check_csrf(request)

        # voting has not started or has ended
        if (not election.voting_has_started()) or election.voting_has_stopped():
            return HttpResponseRedirect(settings.URL_HOST)

        # if user is not logged in
        # bring back to the confirmation page to let him know
        if not voter:
            return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_cast_confirm, args=[election.uuid]))

        # don't store the vote in the voter's data structure until verification
        cast_vote.save()

        # status update?
        if request.POST.get('status_update', False):
            status_update_message = request.POST.get('status_update_message')
        else:
            status_update_message = None

        # launch the verification task

        tasks.cast_vote_verify_and_store.delay(
            cast_vote_id=cast_vote.id,
            status_update_message=status_update_message)

        # remove the vote from the store
        del request.session['encrypted_vote']

        return HttpResponseRedirect("%s%s" % (settings.URL_HOST, reverse(one_election_cast_done, args=[election.uuid])))


@election_view()
def one_election_cast_done(request, election):
    """
    This view needs to be loaded because of the IFRAME, but then this causes 
    problems if someone clicks "reload". So we need a strategy.
    We store the ballot hash in the session
    """
    user = get_user(request)
    voter = get_voter(request, user, election)

    if voter:
        votes = CastVote.get_by_voter(voter)
        vote_hash = votes[0].vote_hash
        cv_url = get_castvote_url(votes[0])

        # only log out if the setting says so *and* we're dealing
        # with a site-wide voter. Definitely remove current_voter
        if voter.user == user:
            logout = settings.LOGOUT_ON_CONFIRMATION
        else:
            logout = False
            del request.session['CURRENT_VOTER']

        save_in_session_across_logouts(request, 'last_vote_hash', vote_hash)
        save_in_session_across_logouts(request, 'last_vote_cv_url', cv_url)
    else:
        vote_hash = request.session['last_vote_hash']
        cv_url = request.session['last_vote_cv_url']
        logout = False

    # local logout ensures that there's no more
    # user locally
    # WHY DO WE COMMENT THIS OUT? because we want to force a full logout via the iframe, including
    # from remote systems, just in case, i.e. CAS
    # if logout:
    #   auth_views.do_local_logout(request)

    # tweet/fb your vote
    socialbuttons_url = get_socialbuttons_url(
        cv_url, 'I cast a vote in %s' % election.name)

    # remote logout is happening asynchronously in an iframe to be modular given the logout mechanism
    # include_user is set to False if logout is happening
    return render_template(request, 'election_cast_done', {'election': election,
                                                  'vote_hash': vote_hash, 'logout': logout,
                                                  'socialbuttons_url': socialbuttons_url},
                           include_user=(not logout))


@election_view()
@json
def one_election_result(request, election):
    return election.result


@election_view()
@json
def one_election_result_proof(request, election):
    return election.result_proof


@election_view(frozen=True)
def one_election_bboard(request, election):
    """
    UI to show election bboard
    """
    after = request.GET.get('after', None)
    offset = int(request.GET.get('offset', 0))
    limit = int(request.GET.get('limit', 50))

    order_by = 'voter_id'

    # unless it's by alias, in which case we better go by UUID
    if election.use_voter_aliases:
        order_by = 'alias'

    # if there's a specific voter
    if request.GET.has_key('q'):
        # FIXME: figure out the voter by voter_id
        voters = []
    else:
        # load a bunch of voters
        voters = Voter.get_by_election(
            election, after=after, limit=limit + 1, order_by=order_by)

    more_p = len(voters) > limit
    if more_p:
        voters = voters[0:limit]
        next_after = getattr(voters[limit - 1], order_by)
    else:
        next_after = None

    return render_template(request, 'election_bboard', {'election': election, 'voters': voters, 'next_after': next_after,
                                                        'offset': offset, 'limit': limit, 'offset_plus_one': offset + 1, 'offset_plus_limit': offset + limit,
                                                        'voter_id': request.GET.get('voter_id', '')})


@election_view(frozen=True)
def one_election_audited_ballots(request, election):
    """
    UI to show election audited ballots
    """

    if request.GET.has_key('vote_hash'):
        b = AuditedBallot.get(election, request.GET['vote_hash'])
        return HttpResponse(b.raw_vote, mimetype="text/plain")

    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 50))

    audited_ballots = AuditedBallot.get_by_election(election)

    audited_ballots_paginator = Paginator(audited_ballots, limit)
    audited_ballots_page = audited_ballots_paginator.page(page)

    return render_template(request, 'election_audited_ballots', {'election': election, 'audited_ballots_paginator': audited_ballots_paginator,
                                                                 'audited_ballots_page': audited_ballots_page, 'audited_ballots': audited_ballots_page.object_list, 'page': page, 'limit': limit})


@election_admin()
def voter_delete(request, election, voter_uuid):
    """
    Two conditions under which a voter can be deleted:
    - election is not frozen or
    - election is open reg
    """
    # FOR NOW we allow this to see if we can redefine the meaning of "closed reg" to be more flexible
    # if election is frozen and has closed registration
    # if election.frozen_at and (not election.openreg):
    #  raise PermissionDenied()

    if election.encrypted_tally:
        raise PermissionDenied()

    voter = Voter.get_by_election_and_uuid(election, voter_uuid)
    if voter:
        voter.delete()

    if election.frozen_at:
        # log it
        election.append_log(
            "Voter %s/%s removed after election frozen" % (voter.voter_type, voter.voter_id))

    return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(voters_list_pretty, args=[election.uuid]))


@election_admin(frozen=False)
def one_election_set_reg(request, election):
    """
    Set whether this is open registration or not
    """
    # only allow this for public elections
    if not election.private_p:
        open_p = bool(int(request.GET['open_p']))
        election.openreg = open_p
        election.save()

    return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(voters_list_pretty, args=[election.uuid]))


@election_admin()
def one_election_set_featured(request, election):
    """
    Set whether this is a featured election or not
    """

    user = get_user(request)
    if not security.user_can_feature_election(user, election):
        raise PermissionDenied()

    featured_p = bool(int(request.GET['featured_p']))
    election.featured_p = featured_p
    election.save()

    return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))


@election_admin()
def one_election_archive(request, election):

    archive_p = request.GET.get('archive_p', True)

    if bool(int(archive_p)):
        election.archived_at = datetime.datetime.utcnow()
    else:
        election.archived_at = None

    election.save()

    return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))

# changed from admin to view because
# anyone can see the questions, the administration aspect is now
# built into the page


@election_view()
def one_election_questions(request, election):
    questions_json = utils.to_json(election.questions)
    user = get_user(request)
    admin_p = security.user_can_admin_election(user, election)

    return render_template(request, 'election_questions', {'election': election, 'questions_json': questions_json, 'admin_p': admin_p})


def _check_eligibility(election, user):
    # prevent password-users from signing up willy-nilly for other elections,
    # doesn't make sense
    if user.user_type == 'password':
        return False

    return election.user_eligible_p(user)


def _register_voter(election, user):
    if not _check_eligibility(election, user):
        return None

    return Voter.register_user_in_election(user, election)


@election_view()
def one_election_register(request, election):
    if not election.openreg:
        return HttpResponseForbidden('registration is closed for this election')

    check_csrf(request)

    user = get_user(request)
    voter = Voter.get_by_election_and_user(election, user)

    if not voter:
        voter = _register_voter(election, user)

    return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))


@election_admin(frozen=False)
def one_election_save_questions(request, election):
    check_csrf(request)

    election.questions = utils.from_json(request.POST['questions_json'])
    election.save()

    # always a machine API
    return SUCCESS


@transaction.commit_on_success
@election_admin(frozen=False)
def one_election_freeze(request, election):
    # figure out the number of questions and trustees
    issues = election.issues_before_freeze

    if request.method == "GET":
        return render_template(request, 'election_freeze', {'election': election, 'issues': issues, 'issues_p': len(issues) > 0})
    else:
        check_csrf(request)

        election.freeze()

        if get_user(request):
            return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))
        else:
            return SUCCESS


def _check_election_tally_type(election):
    for q in election.questions:
        if q['tally_type'] != "homomorphic":
            return False
    return True


@election_admin(frozen=True)
def one_election_compute_tally(request, election):
    """
    tallying is done all at a time now
    """
    if not _check_election_tally_type(election):
        return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.election_id]))

    if request.method == "GET":
        return render_template(request, 'election_compute_tally', {'election': election})

    check_csrf(request)

    if not election.voting_ended_at:
        election.voting_ended_at = datetime.datetime.utcnow()

    election.tallying_started_at = datetime.datetime.utcnow()
    election.save()

    tasks.election_compute_tally.delay(election_id=election.id)

    return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))


@trustee_check
def trustee_decrypt_and_prove(request, election, trustee):
    if not _check_election_tally_type(election) or election.encrypted_tally == None:
        return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))

    return render_template(request, 'trustee_decrypt_and_prove', {'election': election, 'trustee': trustee})


@election_view(frozen=True)
def trustee_upload_decryption(request, election, trustee_uuid):
    if not _check_election_tally_type(election) or election.encrypted_tally == None:
        return FAILURE

    trustee = Trustee.get_by_election_and_uuid(election, trustee_uuid)

    factors_and_proofs = utils.from_json(request.POST['factors_and_proofs'])

    # verify the decryption factors
    trustee.decryption_factors = [[datatypes.LDObject.fromDict(
        factor, type_hint='core/BigInteger').wrapped_obj for factor in one_q_factors] for one_q_factors in factors_and_proofs['decryption_factors']]

    # each proof needs to be deserialized
    trustee.decryption_proofs = [[datatypes.LDObject.fromDict(
        proof, type_hint='legacy/EGZKProof').wrapped_obj for proof in one_q_proofs] for one_q_proofs in factors_and_proofs['decryption_proofs']]

    if trustee.verify_decryption_proofs():
        trustee.save()

        try:
            # send a note to admin
            election.admin.send_message("%s - trustee partial decryption" % election.name,
                                        "trustee %s (%s) did their partial decryption." % (trustee.name, trustee.email))
        except:
            # ah well
            pass

        return SUCCESS
    else:
        return FAILURE


@election_admin(frozen=True)
def combine_decryptions(request, election):
    """
    combine trustee decryptions
    """

    election_url = get_election_url(election)

    if request.method == "POST":
        check_csrf(request)

        election.combine_decryptions()
        election.save()

        return HttpResponseRedirect("%s?%s" % (settings.SECURE_URL_HOST + reverse(voters_email, args=[election.uuid]), urllib.urlencode({'template': 'result'})))

    # if just viewing the form or the form is not valid
    return render_template(request, 'combine_decryptions', {'election': election})


@election_admin(frozen=True)
def one_election_set_result_and_proof(request, election):
    if election.tally_type != "homomorphic" or election.encrypted_tally == None:
        return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.id]))

    # FIXME: check csrf

    election.result = utils.from_json(request.POST['result'])
    election.result_proof = utils.from_json(request.POST['result_proof'])
    election.save()

    if get_user(request):
        return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))
    else:
        return SUCCESS


@election_view()
def voters_list_pretty(request, election):
    """
    Show the list of voters
    now using Django pagination
    """

    # for django pagination support
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 50))
    q = request.GET.get('q', '')

    order_by = 'user__user_id'

    # unless it's by alias, in which case we better go by UUID
    if election.use_voter_aliases:
        order_by = 'alias'

    user = get_user(request)
    admin_p = security.user_can_admin_election(user, election)

    categories = None
    eligibility_category_id = None

    try:
        if admin_p and can_list_categories(user.user_type):
            categories = AUTH_SYSTEMS[user.user_type].list_categories(user)
            eligibility_category_id = election.eligibility_category_id(
                user.user_type)
    except AuthenticationExpired:
        return user_reauth(request, user)

    # files being processed
    voter_files = election.voterfile_set.all()

    # load a bunch of voters
    # voters = Voter.get_by_election(election, order_by=order_by)
    voters = Voter.objects.filter(
        election=election).order_by(order_by).defer('vote')

    if q != '':
        if election.use_voter_aliases:
            voters = voters.filter(alias__icontains=q)
        else:
            voters = voters.filter(voter_name__icontains=q)

    voters_paginator = Paginator(voters, limit)
    voters_page = voters_paginator.page(page)

    return render_template(request, 'voters_list',
                           {'election': election,
                            'voters_paginator': voters_paginator,
                            'voters_page': voters_page,
                            'voters': voters_page.object_list,
                            'admin_p': admin_p,
                            'email_voters': helios.VOTERS_EMAIL,
                            'limit': limit,
                            'upload_p': helios.VOTERS_UPLOAD, 'q': q,
                            'voter_files': voter_files,
                            'categories': categories,
                            'eligibility_category_id': eligibility_category_id})


@election_admin()
def voters_eligibility(request, election):
    """
    set eligibility for voters
    """
    user = get_user(request)

    if request.method == "GET":
        # this shouldn't happen, only POSTs
        return HttpResponseRedirect("/")

    # for now, private elections cannot change eligibility
    if election.private_p:
        return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(voters_list_pretty, args=[election.uuid]))

    # eligibility
    eligibility = request.POST['eligibility']

    if eligibility in ['openreg', 'limitedreg']:
        election.openreg = True

    if eligibility == 'closedreg':
        election.openreg = False

    if eligibility == 'limitedreg':
        # now process the constraint
        category_id = request.POST['category_id']

        constraint = AUTH_SYSTEMS[
            user.user_type].generate_constraint(category_id, user)
        election.eligibility = [
            {'auth_system': user.user_type, 'constraint': [constraint]}]
    else:
        election.eligibility = None

    election.save()
    return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(voters_list_pretty, args=[election.uuid]))


@election_admin()
def voters_upload(request, election):
    """
    Upload a CSV of password-based voters with
    voter_id, email, name

    name and email are needed only if voter_type is static
    """

    # TRYING this: allowing voters upload by admin when election is frozen
    # if election.frozen_at and not election.openreg:
    #  raise PermissionDenied()

    if request.method == "GET":
        return render_template(request, 'voters_upload', {'election': election, 'error': request.GET.get('e', None)})

    if request.method == "POST":
        if bool(request.POST.get('confirm_p', 0)):
            # launch the background task to parse that file
            tasks.voter_file_process.delay(
                voter_file_id=request.session['voter_file_id'])
            del request.session['voter_file_id']

            return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(voters_list_pretty, args=[election.uuid]))
        else:
            # we need to confirm
            if request.FILES.has_key('voters_file'):
                voters_file = request.FILES['voters_file']
                voter_file_obj = election.add_voters_file(voters_file)

                request.session['voter_file_id'] = voter_file_obj.id

                # import the first few lines to check
                voters = [v for v in voter_file_obj.itervoters()][:5]

                return render_template(request, 'voters_upload_confirm', {'election': election, 'voters': voters})
            else:
                return HttpResponseRedirect("%s?%s" % (settings.SECURE_URL_HOST + reverse(voters_upload, args=[election.uuid]), urllib.urlencode({'e': 'No voter file specified, please try again.'})))


@election_admin()
def voters_upload_cancel(request, election):
    """
    cancel upload of CSV file
    """
    voter_file_id = request.session.get('voter_file_id', None)
    if voter_file_id:
        vf = VoterFile.objects.get(id=voter_file_id)
        vf.delete()
    del request.session['voter_file_id']

    return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))


@election_admin(frozen=True)
def voters_email(request, election):
    if not helios.VOTERS_EMAIL:
        return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))
    TEMPLATES = [
        ('vote', 'Time to Vote'),
        ('info', 'Additional Info'),
        ('result', 'Election Result')
    ]

    template = request.REQUEST.get('template', 'vote')
    if not template in [t[0] for t in TEMPLATES]:
        raise Exception("bad template")

    voter_id = request.REQUEST.get('voter_id', None)

    if voter_id:
        voter = Voter.get_by_election_and_voter_id(election, voter_id)
    else:
        voter = None

    election_url = get_election_url(election)
    election_vote_url = get_election_govote_url(election)

    default_subject = render_template_raw(None, 'email/%s_subject.txt' % template, {
        'custom_subject': "&lt;SUBJECT&gt;"
    })
    default_body = render_template_raw(None, 'email/%s_body.txt' % template, {
        'election': election,
        'election_url': election_url,
        'election_vote_url': election_vote_url,
        'custom_subject': default_subject,
        'custom_message': '&lt;BODY&gt;',
        'voter': {'vote_hash': '<SMART_TRACKER>',
                  'name': '<VOTER_NAME>',
                  'voter_login_id': '<VOTER_LOGIN_ID>',
                  'voter_password': '<VOTER_PASSWORD>',
                  'voter_type': election.voter_set.all()[0].voter_type,
                  'election': election}
    })

    if request.method == "GET":
        email_form = forms.EmailVotersForm()
        if voter:
            email_form.fields['send_to'].widget = email_form.fields[
                'send_to'].hidden_widget()
    else:
        email_form = forms.EmailVotersForm(request.POST)

        if email_form.is_valid():

            # the client knows to submit only once with a specific voter_id
            subject_template = 'email/%s_subject.txt' % template
            body_template = 'email/%s_body.txt' % template

            extra_vars = {
                'custom_subject': email_form.cleaned_data['subject'],
                'custom_message': email_form.cleaned_data['body'],
                'election_vote_url': election_vote_url,
                'election_url': election_url,
                'election': election
            }

            voter_constraints_include = None
            voter_constraints_exclude = None

            if voter:
                tasks.single_voter_email.delay(
                    voter_uuid=voter.uuid, subject_template=subject_template, body_template=body_template, extra_vars=extra_vars)
            else:
                # exclude those who have not voted
                if email_form.cleaned_data['send_to'] == 'voted':
                    voter_constraints_exclude = {'vote_hash': None}

                # include only those who have not voted
                if email_form.cleaned_data['send_to'] == 'not-voted':
                    voter_constraints_include = {'vote_hash': None}

                tasks.voters_email.delay(election_id=election.id, subject_template=subject_template, body_template=body_template,
                                         extra_vars=extra_vars, voter_constraints_include=voter_constraints_include, voter_constraints_exclude=voter_constraints_exclude)

            # this batch process is all async, so we can return a nice note
            return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))

    return render_template(request, "voters_email", {
        'email_form': email_form, 'election': election,
        'voter': voter,
        'default_subject': default_subject,
        'default_body': default_body,
        'template': template,
        'templates': TEMPLATES})

# Individual Voters


@election_view()
@json
def voter_list(request, election):
    # normalize limit
    limit = int(request.GET.get('limit', 500))
    if limit > 500:
        limit = 500

    voters = Voter.get_by_election(
        election, order_by='uuid', after=request.GET.get('after', None), limit=limit)
    return [v.ld_object.toDict() for v in voters]


@election_view()
@json
def one_voter(request, election, voter_uuid):
    """
    View a single voter's info as JSON.
    """
    voter = Voter.get_by_election_and_uuid(election, voter_uuid)
    if not voter:
        raise Http404
    return voter.toJSONDict()


@election_view()
@json
def voter_votes(request, election, voter_uuid):
    """
    all cast votes by a voter
    """
    voter = Voter.get_by_election_and_uuid(election, voter_uuid)
    votes = CastVote.get_by_voter(voter)
    return [v.toJSONDict() for v in votes]


@election_view()
@json
def voter_last_vote(request, election, voter_uuid):
    """
    all cast votes by a voter
    """
    voter = Voter.get_by_election_and_uuid(election, voter_uuid)
    return voter.last_cast_vote().toJSONDict()

##
# cast ballots
##


@election_view()
@json
def ballot_list(request, election):
    """
    this will order the ballots from most recent to oldest.
    and optionally take a after parameter.
    """
    limit = after = None
    if request.GET.has_key('limit'):
        limit = int(request.GET['limit'])
    if request.GET.has_key('after'):
        after = datetime.datetime.strptime(
            request.GET['after'], '%Y-%m-%d %H:%M:%S')

    voters = Voter.get_by_election(
        election, cast=True, order_by='cast_at', limit=limit, after=after)

    # we explicitly cast this to a short cast vote
    return [v.last_cast_vote().ld_object.short.toDict(complete=True) for v in voters]
