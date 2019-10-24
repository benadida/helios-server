"""
Plugin for Pyramid apps to submit errors to Rollbar
"""

import logging
import sys

from pyramid.httpexceptions import WSGIHTTPException
from pyramid.tweens import EXCVIEW
from pyramid.util import DottedNameResolver
from pyramid.settings import asbool

import rollbar

DEFAULT_WEB_BASE = 'https://rollbar.com'

log = logging.getLogger(__name__)

def handle_error(settings, request):
    rollbar.report_exc_info(sys.exc_info(), request)


def parse_settings(settings):
    prefix = 'rollbar.'
    out = {}
    for k, v in settings.items():
        if k.startswith(prefix):
            out[k[len(prefix):]] = v
    return out


def rollbar_tween_factory(pyramid_handler, registry):
    settings = parse_settings(registry.settings)

    whitelist = ()
    blacklist = (WSGIHTTPException,)

    def rollbar_tween(request):
        # for testing out the integration
        try:
            if (settings.get('allow_test', 'true') == 'true' and
                request.GET.get('pyramid_rollbar_test') == 'true'):
                try:
                    raise Exception("pyramid_rollbar test exception")
                except:
                    handle_error(settings, request)
        except:
            log.exception("Error in pyramid_rollbar_test block")

        try:
            response = pyramid_handler(request)
        except whitelist:
            handle_error(settings, request)
            raise
        except blacklist:
            raise
        except:
            handle_error(settings, request)
            raise
        return response

    return rollbar_tween


def patch_debugtoolbar(settings):
    """
    Patches the pyramid_debugtoolbar (if installed) to display a link to the related rollbar item.
    """
    try:
        from pyramid_debugtoolbar import tbtools
    except ImportError:
        return

    rollbar_web_base = settings.get('rollbar.web_base', DEFAULT_WEB_BASE)
    if rollbar_web_base.endswith('/'):
        rollbar_web_base = rollbar_web_base[:-1]

    def insert_rollbar_console(request, html):
        # insert after the closing </h1>
        item_uuid = request.environ.get('rollbar.uuid')
        if not item_uuid:
            return html

        url = '%s/item/uuid/?uuid=%s' % (rollbar_web_base, item_uuid)
        link = '<a style="color:white;" href="%s">View in Rollbar</a>' % url
        new_data = "<h2>Rollbar: %s</h2>" % link
        insertion_marker = "</h1>"
        replacement = insertion_marker + new_data
        return html.replace(insertion_marker, replacement, 1)

    # patch tbtools.Traceback.render_full
    old_render_full = tbtools.Traceback.render_full
    def new_render_full(self, request, *args, **kw):
        html = old_render_full(self, request, *args, **kw)
        return insert_rollbar_console(request, html)
    tbtools.Traceback.render_full = new_render_full


def includeme(config):
    """
    Pyramid entry point
    """
    settings = config.registry.settings

    config.add_tween('rollbar.contrib.pyramid.rollbar_tween_factory', under=EXCVIEW)

    # run patch_debugtoolbar, unless they disabled it
    if asbool(settings.get('rollbar.patch_debugtoolbar', True)):
        patch_debugtoolbar(settings)

    def hook(request, data):
        data['framework'] = 'pyramid'

        if request:
            request.environ['rollbar.uuid'] = data['uuid']

            if request.matched_route:
                data['context'] = request.matched_route.name

    rollbar.BASE_DATA_HOOK = hook

    kw = parse_settings(settings)

    access_token = kw.pop('access_token')
    environment = kw.pop('environment', 'production')

    if kw.get('scrub_fields'):
        kw['scrub_fields'] = set([str.strip(x) for x in kw.get('scrub_fields').split('\n') if x])

    if kw.get('exception_level_filters'):
        r = DottedNameResolver()
        exception_level_filters = []
        for line in kw.get('exception_level_filters').split('\n'):
            if line:
                dotted_path, level = line.split()

                try:
                    cls = r.resolve(dotted_path)
                    exception_level_filters.append((cls, level))
                except ImportError:
                    log.error('Could not import %r' % dotted_path)

        kw['exception_level_filters'] = exception_level_filters

    kw['enabled'] = asbool(kw.get('enabled', True))

    rollbar.init(access_token, environment, **kw)


def create_rollbar_middleware(app, global_config=None, **kw):
    access_token = kw.pop('access_token')
    environment = kw.pop('environment', 'production')

    rollbar.init(access_token, environment, **kw)
    return RollbarMiddleware(global_config or {}, app)


class RollbarMiddleware(object):
    def __init__(self, settings, app):
        self.settings = settings
        self.app = app

    def __call__(self, environ, start_resp):
        try:
            return self.app(environ, start_resp)
        except Exception as e:
            from pyramid.request import Request
            handle_error(self.settings, Request(environ))
            raise
