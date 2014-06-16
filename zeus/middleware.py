import uuid
import logging

from django.conf import settings
from django.http import HttpResponseRedirect

from zeus import auth

logger = logging.getLogger()



class ForceDefaultLanguageMiddleware(object):
    """
    Ignore Accept-Language HTTP headers

    This will force the I18N machinery to always choose settings.LANGUAGE_CODE
    as the default initial language, unless another one is set via sessions or cookies

    Should be installed *before* any middleware that checks request.META['HTTP_ACCEPT_LANGUAGE'],
    namely django.middleware.locale.LocaleMiddleware
    """
    def process_request(self, request):
        if request.META.has_key('HTTP_ACCEPT_LANGUAGE'):
            del request.META['HTTP_ACCEPT_LANGUAGE']

	lang = request.GET.get('lang')
        if lang:
            request.session['django_language'] = lang
            return HttpResponseRedirect('/' + settings.SERVER_PREFIX + '/')
	

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
