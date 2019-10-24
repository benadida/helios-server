"""
django-rollbar middleware

To install, add the following in your settings.py:
1. add 'rollbar.contrib.django.middleware.RollbarNotifierMiddleware' to MIDDLEWARE_CLASSES 
2. add a section like this:
ROLLBAR = {
    'access_token': 'tokengoeshere',
}

See README.rst for full installation and configuration instructions.
"""

import logging
import sys

import rollbar

from django.core.exceptions import MiddlewareNotUsed
from django.core.urlresolvers import resolve
from django.conf import settings
from django.http import Http404

log = logging.getLogger(__name__)


DEFAULTS = {
    'web_base': 'https://rollbar.com',
    'enabled': True,
    'patch_debugview': True,
    'exception_level_filters': [
        (Http404, 'warning')
    ]
}


def _patch_debugview(rollbar_web_base):
    try:
        from django.views import debug
    except ImportError:
        return
    
    if rollbar_web_base.endswith('/'):
        rollbar_web_base = rollbar_web_base[:-1]
    
    # modify the TECHNICAL_500_TEMPLATE
    new_data = """
{% if view_in_rollbar_url %}
  <h3 style="margin-bottom:15px;"><a href="{{ view_in_rollbar_url }}" target="_blank">View in Rollbar</a></h3>
{% endif %}
    """

    if new_data in debug.TECHNICAL_500_TEMPLATE:
        return

    insert_before = '<table class="meta">'
    replacement = new_data + insert_before
    debug.TECHNICAL_500_TEMPLATE = debug.TECHNICAL_500_TEMPLATE.replace(insert_before, 
        replacement, 1)

    # patch ExceptionReporter.get_traceback_data
    old_get_traceback_data = debug.ExceptionReporter.get_traceback_data
    def new_get_traceback_data(exception_reporter):
        data = old_get_traceback_data(exception_reporter)
        try:
            item_uuid = exception_reporter.request.META.get('rollbar.uuid')
            if item_uuid:
                url = '%s/item/uuid/?uuid=%s' % (rollbar_web_base, item_uuid)
                data['view_in_rollbar_url'] = url
        except:
            log.exception("Exception while adding view-in-rollbar link to technical_500_template.")
        return data
    debug.ExceptionReporter.get_traceback_data = new_get_traceback_data


class RollbarNotifierMiddleware(object):
    def __init__(self):
        self.settings = getattr(settings, 'ROLLBAR', {})
        if not self.settings.get('access_token'):
            raise MiddlewareNotUsed

        if not self._get_setting('enabled'):
            raise MiddlewareNotUsed
        
        self._ensure_log_handler()
        
        kw = self.settings.copy()
        access_token = kw.pop('access_token')
        environment = kw.pop('environment', 'development' if settings.DEBUG else 'production')
        kw.setdefault('exception_level_filters', DEFAULTS['exception_level_filters'])
        
        rollbar.init(access_token, environment, **kw)
        
        def hook(request, data):
            try:
                # try django 1.5 method for getting url_name
                url_name = request.resolver_match.url_name
            except:
                # fallback to older method
                try:
                    url_name = resolve(request.path_info).url_name
                except:
                    url_name = None

            if url_name:
                data['context'] = url_name

            data['framework'] = 'django'
            
            if request:
                request.META['rollbar.uuid'] = data['uuid']
            
        rollbar.BASE_DATA_HOOK = hook
        
        # monkeypatch debug module
        if self._get_setting('patch_debugview'):
            try:
                _patch_debugview(self._get_setting('web_base'))
            except Exception as e:
                log.error("Rollbar - unable to monkeypatch debugview to add 'View in Rollbar' link."
                    " To disable, set `ROLLBAR['patch_debugview'] = False` in settings.py."
                    " Exception was: %r", e)

    def _ensure_log_handler(self):
        """
        If there's no log configuration, set up a default handler.
        """
        if log.handlers:
            return
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)-5.5s [%(name)s][%(threadName)s] %(message)s')
        handler.setFormatter(formatter)
        log.addHandler(handler)
    
    def _get_setting(self, name, default=None):
        try:
            return self.settings[name]
        except KeyError:
            if name in DEFAULTS:
                default_val = DEFAULTS[name]
                if hasattr(default_val, '__call__'):
                    return default_val()
                return default_val
            return default

    def process_response(self, request, response):
        return response

    def process_exception(self, request, exc):
        rollbar.report_exc_info(sys.exc_info(), request)
