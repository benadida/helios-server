import uuid
import threading

from functools import wraps

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect

from helios.models import Election, Poll, Trustee, Voter
from heliosauth.models import User

from zeus.log import init_election_logger, init_poll_logger, _locals

import logging
logger = logging.getLogger(__name__)


def get_ip(request):
    ip = request.META.get('HTTP_X_FORWARDER_FOR', None)
    if not ip:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def trustee_view(func):
    @wraps(func)
    @election_view()
    def wrapper(request, election, *args, **kwargs):
        if not request.zeususer.is_trustee:
            raise PermissionDenied("Only election trustees can access this"
                                   "view")
        kwargs['trustee'] = request.trustee
        kwargs['election'] = election
        return func(request, *args, **kwargs)
    return wrapper


def election_view(check_access=True):
    def wrapper(func):
        @wraps(func)
        def inner(request, *args, **kwargs):
            user = request.zeususer
            if user.is_authenticated():
                _locals.user_id = user.user_id
            _locals.ip = get_ip(request)
            if 'election_uuid' in kwargs:
                uuid = kwargs.pop('election_uuid')
                election = get_object_or_404(Election, uuid=uuid)
                if not user.can_access_election(election) and check_access:
                    raise PermissionDenied("Election cannot be accessed by you")
                kwargs['election'] = election

            if 'poll_uuid' in kwargs:
                uuid = kwargs.pop('poll_uuid')
                poll = get_object_or_404(Poll, uuid=uuid)
                if not user.can_access_poll(poll) and check_access:
                    raise PermissionDenied("Poll cannot be accessed by you")
                kwargs['poll'] = poll

            return func(request, *args, **kwargs)
        return inner
    return wrapper


def poll_voter_required(func):
    @election_view()
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.zeususer.is_voter:
            raise PermissionDenied("Authenticated user required")
        return func(request, *args, **kwargs)
    return wrapper


def user_required(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.zeususer or not request.zeususer.is_authenticated():
            raise PermissionDenied("Authenticated user required")
        return func(request, *args, **kwargs)
    return wrapper

def superadmin_required(func):
    @user_required
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.zeususer._user.superadmin_p:
            raise PermissionDenied("Superadmin user required")
        return func(request, *args, **kwargs)
    return wrapper

def manager_or_superadmin_required(func):
    @user_required
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not (request.zeususer._user.superadmin_p
                or request.zeususer.is_manager):
            raise PersmissionDenied("Superadmin or manager required")
        return func(request, *args, **kwargs)
    return wrapper

def election_poll_required(func):
    @election_view(check_access=True)
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.zeususer.is_voter:
            raise PermissionDenied("Authenticated user required")
        return func(request, *args, **kwargs)
    return wrapper

def election_user_required(func):
    @wraps(func)
    @election_view()
    @user_required
    def wrapper(request, *args, **kwargs):
        return func(request, *args, **kwargs)
    return wrapper


def election_admin_required(func):
    @wraps(func)
    @election_view()
    @user_required
    def wrapper(request, *args, **kwargs):
        user = request.zeususer
        if not user.is_admin:
            raise PermissionDenied("Elections administrator required")
        return func(request, *args, **kwargs)

    return wrapper


def unauthenticated_user_required(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if request.zeususer.is_authenticated():
            raise PermissionDenied("Please logout to access this view")
        return func(request, *args, **kwargs)
    return wrapper


def requires_election_features(*features):
    def wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            election = kwargs.get('election')
            if not election.check_features(*features):
                status = election.check_features_verbose(*features)
                msg = ("Unmet election %s required "
                      "features %r") % (election.uuid, status)
                logger.error(msg)
                raise PermissionDenied(msg)
            return func(*args, **kwargs)
        return inner
    return wrapper



def requires_poll_features(*features):
    def wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            poll = kwargs.get('poll')
            if not poll.check_features(*features):
                status = poll.check_features_verbose(*features)
                msg = ("Unmet poll %s required "
                       "features %r") % (poll.uuid, status)
                logger.error(msg)
                raise PermissionDenied(msg)
            return func(*args, **kwargs)
        return inner
    return wrapper


TRUSTEE_SESSION_KEY = 'zeus_trustee_uuid'
USER_SESSION_KEY = 'user'
VOTER_SESSION_KEY = 'CURRENT_VOTER'


class ZeusUser(object):

    is_user = False
    is_trustee = False
    is_voter = False
    is_admin = False
    is_manager = False
    is_superadmin = False

    @classmethod
    def from_request(self, request):
        user = None
        try:
            users = get_users_from_request(request)
            user = filter(lambda x:bool(x), users)[0]
        except IndexError:
            pass
        return ZeusUser(user)

    def __init__(self, user_obj):
        self._user = user_obj
        if isinstance(self._user, User):
            self.is_user = True
            if self._user.superadmin_p:
                self.is_superadmin = True
            if self._user.management_p:
                self.is_manager = True
            if self._user.admin_p or self._user.superadmin_p:
                self.is_admin = True
                self.institution = self._user.institution
                return
            return

        if isinstance(self._user, Trustee):
            self.is_trustee = True

        if isinstance(self._user, Voter):
            if not self._user.excluded_at:
                self.is_voter = True

    @property
    def user_id(self):
        if self.is_admin:
            return "ADMIN:%s" % self._user.user_id
        if self.is_trustee:
            return "TRUSTEE:%s" % self._user.email
        if self.is_voter:
            prefix = "VOTER"
            voter = self._user
            if voter.excluded_at:
                prefix = "EXCLUDED_VOTER"
            return "%s:%s" % (prefix, voter.voter_login_id)
        raise Exception("Unknown user")

    def is_authenticated(self):
        return bool(self._user)

    def authenticate(self, request):
        session = request.session

        if self.is_trustee:
            key = TRUSTEE_SESSION_KEY
        if self.is_admin:
            key = USER_SESSION_KEY
        if self.is_voter:
            key = VOTER_SESSION_KEY

        self._clear_session(request)
        session[key] = self._user.pk

    def logout(self, request):
        self._clear_session(request)
        self._user = None
        self.is_voter = False
        self.is_admin = False
        self.is_trustee = False
        self.is_manager = False
        self.is_superadmin = False

    def _clear_session(self, request):
        for sess_key in [TRUSTEE_SESSION_KEY, USER_SESSION_KEY,
                         VOTER_SESSION_KEY]:
            if sess_key in request.session:
                del request.session[sess_key]

    def can_access_poll(self, poll):
        if self.is_voter:
            return self._user.poll.uuid == poll.uuid
        if self.is_admin:
            if self._user.superadmin_p:
                return True
            return self._user.elections.filter(polls__in=[poll]).count() > 0
        if self.is_trustee:
            return self._user.election.polls.filter(
                pk__in=[poll.pk]).count() > 0
        return False

    def can_access_election(self, election):
        if self.is_voter:
            return self._user.poll.election.uuid == election.uuid
        if self.is_trustee:
            return self._user.election == election
        if self.is_admin:
            if self._user.superadmin_p:
                return True
            return self._user.elections.filter(
                pk__in=[election.pk]).count() > 0
        return False


def get_users_from_request(request):
    session = request.session
    user, admin, trustee, voter = None, None, None, None

    # identify user and admin
    if session.has_key(USER_SESSION_KEY):
        user = request.session[USER_SESSION_KEY]
        try:
            user = User.objects.get(pk=user)
            if user.admin_p or user.superadmin_p:
                admin = user
        except User.DoesNotExist:
            pass

    # idenitfy voter
    if request.session.has_key(VOTER_SESSION_KEY):
        voter = request.session[VOTER_SESSION_KEY]

        try:
            voter = Voter.objects.get(pk=voter)
        except Voter.DoesNotExist:
            pass

        if not voter or voter.excluded_at:
            del request.session[VOTER_SESSION_KEY]
            #TODO: move this in middleware ??? raise PermissionDenied

    # idenitfy trustee
    if request.session.get(TRUSTEE_SESSION_KEY, None):
        try:
            trustee_pk = session.get(TRUSTEE_SESSION_KEY, None)
            if trustee_pk:
                trustee = Trustee.objects.get(pk=int(trustee_pk))
        except:
            pass

    if user and not admin:
        del session[USER_SESSION_KEY]
        user = None
        admin = None

    # cleanup duplicate logins
    if len(filter(lambda x:bool(x), [voter, trustee, admin])) > 1:
        if voter:
            if trustee:
                del session[TRUSTEE_SESSION_KEY]
            if admin:
                del session[USER_SESSION_KEY]
        if trustee:
            if admin:
                del session[USER_SESSION_KEY]

    return voter, trustee, admin
