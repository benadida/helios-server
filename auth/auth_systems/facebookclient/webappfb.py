#
# webappfb - Facebook tools for Google's AppEngine "webapp" Framework
#
# Copyright (c) 2009, Max Battcher
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the author nor the names of its contributors may
#       be used to endorse or promote products derived from this software
#       without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
from google.appengine.api import memcache
from google.appengine.ext.webapp import RequestHandler
from facebook import Facebook
import yaml

"""
Facebook tools for Google AppEngine's object-oriented "webapp" framework.
"""

# This global configuration dictionary is for configuration variables
# for Facebook requests such as the application's API key and secret
# key. Defaults to loading a 'facebook.yaml' YAML file. This should be
# useful and familiar for most AppEngine development.
FACEBOOK_CONFIG = yaml.load(file('facebook.yaml', 'r'))

class FacebookRequestHandler(RequestHandler):
    """
    Base class for request handlers for Facebook apps, providing useful
    Facebook-related tools: a local 
    """

    def _fbconfig_value(self, name, default=None):
        """
        Checks the global config dictionary and then for a class/instance
        variable, using a provided default if no value is found.
        """
        if name in FACEBOOK_CONFIG:
            default = FACEBOOK_CONFIG[name]
            
        return getattr(self, name, default)

    def initialize(self, request, response):
        """
        Initialize's this request's Facebook client.
        """
        super(FacebookRequestHandler, self).initialize(request, response)

        app_name = self._fbconfig_value('app_name', '')
        api_key = self._fbconfig_value('api_key', None)
        secret_key = self._fbconfig_value('secret_key', None)

        self.facebook = Facebook(api_key, secret_key,
            app_name=app_name)

        require_app = self._fbconfig_value('require_app', False)
        require_login = self._fbconfig_value('require_login', False)
        need_session = self._fbconfig_value('need_session', False)
        check_session = self._fbconfig_value('check_session', True)

        self._messages = None
        self.redirecting = False

        if require_app or require_login:
            if not self.facebook.check_session(request):
                self.redirect(self.facebook.get_login_url(next=request.path))
                self.redirecting = True
                return
        elif check_session:
            self.facebook.check_session(request) # ignore response

        # NOTE: require_app is deprecated according to modern Facebook login
        #       policies. Included for completeness, but unnecessary.
        if require_app and not self.facebook.added:
            self.redirect(self.facebook.get_add_url(next=request.path))
            self.redirecting = True
            return

        if not (require_app or require_login) and need_session:
            self.facebook.auth.getSession()

    def redirect(self, url, **kwargs):
        """
        For Facebook canvas pages we should use <fb:redirect /> instead of
        a normal redirect.
        """
        if self.facebook.in_canvas:
            self.response.clear()
            self.response.out.write('<fb:redirect url="%s" />' % (url, ))
        else:
            super(FacebookRequestHandler, self).redirect(url, **kwargs)

    def add_user_message(self, kind, msg, detail='', time=15 * 60):
        """
        Add a message to the current user to memcache.
        """
        if self.facebook.uid:
            key = 'messages:%s' % self.facebook.uid
            self._messages = memcache.get(key)
            message = {
                'kind': kind,
                'message': msg,
                'detail': detail,
            }
            if self._messages is not None:
                self._messages.append(message)
            else:
                self._messages = [message]
            memcache.set(key, self._messages, time=time)

    def get_and_delete_user_messages(self):
        """
        Get all of the messages for the current user; removing them.
        """
        if self.facebook.uid:
            key = 'messages:%s' % self.facebook.uid
            if not hasattr(self, '_messages') or self._messages is None:
                self._messages = memcache.get(key)
            memcache.delete(key)
            return self._messages
        return None

class FacebookCanvasHandler(FacebookRequestHandler):
    """
    Request handler for Facebook canvas (FBML application) requests.
    """

    def canvas(self, *args, **kwargs):
        """
        This will be your handler to deal with Canvas requests.
        """
        raise NotImplementedError()

    def get(self, *args):
        """
        All valid canvas views are POSTS.
        """
        # TODO: Attempt to auto-redirect to Facebook canvas?
        self.error(404)

    def post(self, *args, **kwargs):
        """
        Check a couple of simple safety checks and then call the canvas
        handler.
        """
        if self.redirecting: return

        if not self.facebook.in_canvas:
            self.error(404)
            return

        self.canvas(*args, **kwargs)

# vim: ai et ts=4 sts=4 sw=4
