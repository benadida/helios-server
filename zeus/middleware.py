import uuid
import logging

logger = logging.getLogger()

from zeus import auth

class CSRFMiddleware(object):

    def process_request(self, request):
        session = request.session
        csrf = session.get('csrf_token', None)
        if not csrf or type(csrf) != str:
            request.session['csrf_token'] = str(uuid.uuid4())

class AuthenticationMiddleware(object):

    def process_request(self, request):
        user = auth.ZeusUser.from_request(request)
        setattr(request, 'zeususer', user)
        if user.is_admin:
            setattr(request, 'admin', user._user)
        if user.is_voter:
            setattr(request, 'voter', user._user)
        if user.is_trustee:
            setattr(request, 'trustee', user._user)


class ExceptionsMiddleware(object):
    def process_exception(self, request, exception):
        logger.exception(exception)
