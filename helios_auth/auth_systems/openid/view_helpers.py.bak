
from django import http
from django.http import HttpResponseRedirect

from openid.consumer import consumer
from openid.consumer.discover import DiscoveryFailure
from openid.extensions import ax, pape, sreg
from openid.yadis.constants import YADIS_HEADER_NAME, YADIS_CONTENT_TYPE
from openid.server.trustroot import RP_RETURN_TO_URL_TYPE

from . import util

PAPE_POLICIES = [
    'AUTH_PHISHING_RESISTANT',
    'AUTH_MULTI_FACTOR',
    'AUTH_MULTI_FACTOR_PHYSICAL',
    ]

AX_REQUIRED_FIELDS = {
    'firstname' : 'http://axschema.org/namePerson/first',
    'lastname' : 'http://axschema.org/namePerson/last',
    'fullname' : 'http://axschema.org/namePerson',
    'email' : 'http://axschema.org/contact/email'
}

# List of (name, uri) for use in generating the request form.
POLICY_PAIRS = [(p, getattr(pape, p))
                for p in PAPE_POLICIES]

def getOpenIDStore():
    """
    Return an OpenID store object fit for the currently-chosen
    database backend, if any.
    """
    return util.getOpenIDStore('/tmp/djopenid_c_store', 'c_')

def get_consumer(session):
    """
    Get a Consumer object to perform OpenID authentication.
    """
    return consumer.Consumer(session, getOpenIDStore())

def start_openid(session, openid_url, trust_root, return_to):
    """
    Start the OpenID authentication process.

    * Requests some Simple Registration data using the OpenID
      library's Simple Registration machinery

    * Generates the appropriate trust root and return URL values for
      this application (tweak where appropriate)

    * Generates the appropriate redirect based on the OpenID protocol
      version.
    """

    # Start OpenID authentication.
    c = get_consumer(session)
    error = None

    try:
        auth_request = c.begin(openid_url)
    except DiscoveryFailure as e:
        # Some other protocol-level failure occurred.
        error = "OpenID discovery error: %s" % (str(e),)

    if error:
        raise Exception("error in openid")

    # Add Simple Registration request information.  Some fields
    # are optional, some are required.  It's possible that the
    # server doesn't support sreg or won't return any of the
    # fields.
    sreg_request = sreg.SRegRequest(required=['email'],
                                    optional=[])
    auth_request.addExtension(sreg_request)

    # Add Attribute Exchange request information.
    ax_request = ax.FetchRequest()
    # XXX - uses myOpenID-compatible schema values, which are
    # not those listed at axschema.org.

    for k, v in AX_REQUIRED_FIELDS.items():
        ax_request.add(ax.AttrInfo(v, required=True))

    auth_request.addExtension(ax_request)
                
    # Compute the trust root and return URL values to build the
    # redirect information.
    # trust_root = util.getViewURL(request, startOpenID)
    # return_to = util.getViewURL(request, finishOpenID)

    # Send the browser to the server either by sending a redirect
    # URL or by generating a POST form.
    url = auth_request.redirectURL(trust_root, return_to)
    return url

def finish_openid(session, request_args, return_to):
    """
    Finish the OpenID authentication process.  Invoke the OpenID
    library with the response from the OpenID server and render a page
    detailing the result.
    """
    result = {}

    # Because the object containing the query parameters is a
    # MultiValueDict and the OpenID library doesn't allow that, we'll
    # convert it to a normal dict.

    if request_args:
        c = get_consumer(session)

        # Get a response object indicating the result of the OpenID
        # protocol.
        response = c.complete(request_args, return_to)

        # Get a Simple Registration response object if response
        # information was included in the OpenID response.
        sreg_response = {}
        ax_items = {}
        if response.status == consumer.SUCCESS:
            sreg_response = sreg.SRegResponse.fromSuccessResponse(response)

            ax_response = ax.FetchResponse.fromSuccessResponse(response)
            if ax_response:
                for k, v in AX_REQUIRED_FIELDS.items():
                    """
                    the values are the URIs, they are the key into the data
                    the key is the shortname
                    """
                    if v in ax_response.data:
                        ax_items[k] = ax_response.get(v)

        # Map different consumer status codes to template contexts.
        results = {
            consumer.CANCEL:
            {'message': 'OpenID authentication cancelled.'},

            consumer.FAILURE:
            {'error': 'OpenID authentication failed.'},

            consumer.SUCCESS:
            {'url': response.getDisplayIdentifier(),
             'sreg': sreg_response and list(sreg_response.items()),
             'ax': ax_items}
            }

        result = results[response.status]

        if isinstance(response, consumer.FailureResponse):
            # In a real application, this information should be
            # written to a log for debugging/tracking OpenID
            # authentication failures. In general, the messages are
            # not user-friendly, but intended for developers.
            result['failure_reason'] = response.message

    return result

