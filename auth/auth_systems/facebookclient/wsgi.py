"""This is some simple helper code to bridge the Pylons / PyFacebook gap.

There's some generic WSGI middleware, some Paste stuff, and some Pylons
stuff.  Once you put FacebookWSGIMiddleware into your middleware stack,
you'll have access to ``environ["pyfacebook.facebook"]``, which is a
``facebook.Facebook`` object.  If you're using Paste (which includes
Pylons users), you can also access this directly using the facebook
global in this module.

"""

# Be careful what you import.  Don't expect everyone to have Pylons,
# Paste, etc. installed.  Degrade gracefully.

from facebook import Facebook

__docformat__ = "restructuredtext"


# Setup Paste, if available.  This needs to stay in the same module as
# FacebookWSGIMiddleware below.

try:
    from paste.registry import StackedObjectProxy
    from webob.exc import _HTTPMove
    from paste.util.quoting import strip_html, html_quote, no_quote
except ImportError:
    pass
else:
    facebook = StackedObjectProxy(name="PyFacebook Facebook Connection")


    class CanvasRedirect(_HTTPMove):

        """This is for canvas redirects."""

        title = "See Other"
        code = 200
        template = '<fb:redirect url="%(location)s" />'

        def html(self, environ):
            """ text/html representation of the exception """
            body = self.make_body(environ, self.template, html_quote, no_quote)
            return body

class FacebookWSGIMiddleware(object):

    """This is WSGI middleware for Facebook."""

    def __init__(self, app, config, facebook_class=Facebook):
        """Initialize the Facebook middleware.

        ``app``
            This is the WSGI application being wrapped.

        ``config``
            This is a dict containing the keys "pyfacebook.apikey" and
            "pyfacebook.secret".

        ``facebook_class``
            If you want to subclass the Facebook class, you can pass in
            your replacement here.  Pylons users will want to use
            PylonsFacebook.

        """
        self.app = app
        self.config = config
        self.facebook_class = facebook_class

    def __call__(self, environ, start_response):
        config = self.config
        real_facebook = self.facebook_class(config["pyfacebook.apikey"],
                                            config["pyfacebook.secret"])
        registry = environ.get('paste.registry')
        if registry:
            registry.register(facebook, real_facebook)
        environ['pyfacebook.facebook'] = real_facebook
        return self.app(environ, start_response)


# The remainder is Pylons specific.

try:
    import pylons
    from pylons.controllers.util import redirect_to as pylons_redirect_to
    from routes import url_for
except ImportError:
    pass
else:


    class PylonsFacebook(Facebook):

        """Subclass Facebook to add Pylons goodies."""

        def check_session(self, request=None):
            """The request parameter is now optional."""
            if request is None:
                request = pylons.request
            return Facebook.check_session(self, request)

        # The Django request object is similar enough to the Paste
        # request object that check_session and validate_signature
        # should *just work*.

        def redirect_to(self, url):
            """Wrap Pylons' redirect_to function so that it works in_canvas.

            By the way, this won't work until after you call
            check_session().

            """
            if self.in_canvas:
                raise CanvasRedirect(url)
            pylons_redirect_to(url)

        def apps_url_for(self, *args, **kargs):
            """Like url_for, but starts with "http://apps.facebook.com"."""
            return "http://apps.facebook.com" + url_for(*args, **kargs)


    def create_pylons_facebook_middleware(app, config):
        """This is a simple wrapper for FacebookWSGIMiddleware.

        It passes the correct facebook_class.

        """
        return FacebookWSGIMiddleware(app, config,
                                      facebook_class=PylonsFacebook)
