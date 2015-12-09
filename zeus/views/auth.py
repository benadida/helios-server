import logging
import urllib2 
import urllib
import json

JWT_SUPPORT = True
try:
    import jwt
except ImportError:
    jwt = None
    JWT_SUPPORT = False

from django.conf.urls.defaults import *
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest
from django.contrib import messages

from zeus import auth
from zeus.utils import *
from zeus.forms import ChangePasswordForm, VoterLoginForm

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.views.decorators.http import require_http_methods

from helios.view_utils import render_template
from helios.models import Voter, Poll
from zeus.forms import LoginForm
from zeus import auth


logger = logging.getLogger(__name__)


@auth.unauthenticated_user_required
@require_http_methods(["POST", "GET"])
def voter_login(request):
    form_cls = VoterLoginForm
    form = VoterLoginForm()
    if request.method == 'POST':
        form = VoterLoginForm(request.POST)
        if form.is_valid():
            poll = form._voter.poll
            user = auth.ZeusUser(form._voter)
            user.authenticate(request)
            poll.logger.info("Poll voter '%s' logged in (global login view)",
                             form._voter.voter_login_id)
            return HttpResponseRedirect(poll_reverse(poll, 'index'))

    cxt = {'form': form}
    return render_template(request, 'voter_login', cxt)


@auth.unauthenticated_user_required
@require_http_methods(["POST", "GET"])
def password_login_view(request):
    error = None
    if request.method == "GET":
        form = LoginForm()
    else:
        form = LoginForm(request.POST)

    request.session['auth_system_name'] = 'password'

    if request.method == "POST":
        if form.is_valid():
            request.session[auth.USER_SESSION_KEY] = form._user_cache.pk
            logger.info("User %s logged in", form._user_cache.user_id)
            return HttpResponseRedirect(reverse('admin_home'))

    return render_template(request,
                           'login',
                           {'form': form, 'error': error})


def logout(request):
    return_url = request.GET.get('next', reverse('home'))
    logger.info("User %s logged out", request.zeususer.user_id)
    request.zeususer.logout(request)
    return HttpResponseRedirect(return_url)


@auth.user_required
def change_password(request):
    user = request.zeususer

    # only admin users can change password
    if not user.is_admin:
        raise PermissionDenied('32')

    password_changed = request.GET.get('password_changed', None)
    form = ChangePasswordForm(user)
    if request.method == "POST":
        form = ChangePasswordForm(user._user, request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(
                reverse('change_password') + '?password_changed=1')
    return render_template(request, 'change_password',
                           {'form': form,
                            'password_changed': password_changed})

def oauth2_login(request):

    poll_uuid = request.GET.get('state')
    try:
        poll = Poll.objects.get(uuid = poll_uuid)
    except Poll.DoesNotExist:
        return HttpResponseBadRequest(400)
    oauth2 = poll.get_oauth2_module
    if oauth2.can_exchange(request):
        oauth2.exchange(oauth2.get_exchange_url())
        try:
            confirmed, data = oauth2.confirm_email()
            if confirmed:
                voter = Voter.objects.get(poll__uuid=poll_uuid,
                                          uuid=oauth2.voter_uuid)
                user = auth.ZeusUser(voter)
                user.authenticate(request)
                poll.logger.info("Poll voter '%s' logged in",
                                 voter.voter_login_id)
                del request.session['oauth2_voter_uuid']
                del request.session['oauth2_voter_email']
                return HttpResponseRedirect(poll_reverse(poll, 'index'))
            else:
                poll.logger.info("[thirdparty] %s cannot resolve email from %r",
                                 poll.remote_login_display, data)
                messages.error(request, 'oauth2 user does not match voter')
                return HttpResponseRedirect(reverse('error',
                                                    kwargs={'code': 400}))
        except urllib2.HTTPError, e:
            poll.logger.exception(e)
            messages.error(request, 'oauth2 error')
            return HttpResponseRedirect(reverse('error',
                                                kwargs={'code': 400}))
            pass
    else:
        poll.logger.info("[thirdparty] oauth2 '%s' can_exchange failed",
                         poll.remote_login_display)
        messages.error(request, 'oauth2 exchange failed')
        return HttpResponseRedirect(reverse('error', kwargs={'code': 400}))


def jwt_login(request):
    if not JWT_SUPPORT:
        logger.error("JWT login not supported")
        return HttpResponseRedirect(reverse("home"))

    token = request.GET.get('jwt', None)
    if not token:
        return HttpResponseBadRequest(400)
    AUDIENCE = 'zeus' # add to settings
    data = jwt.decode(token, verify=False)   
    aud = data['aud']
    iss = data['iss']
    voter_email = data['sub']
    polls = Poll.objects.filter(jwt_auth=True, jwt_issuer=iss,
                                voters__voter_email=voter_email)
    allowed_polls = []
    voting_urls = []
    for poll in polls:
        jwt_pk = poll.jwt_public_key
        try:
            jwt.decode(token, key=jwt_pk, verify=True)
        except jwt.InvalidTokenError:
            from django.http import HttpResponse
            return HttpResponse('bad token')
