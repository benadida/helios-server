import re

from rollbar.lib import iteritems, map, urlsplit, urlencode, urlunsplit, parse_qs, string_types, binary_type
from rollbar.lib.transforms.scrub import ScrubTransform


_starts_with_auth_re = re.compile(r'^[a-zA-Z0-9-_]*(:[^@/]+)?@')


class ScrubUrlTransform(ScrubTransform):
    def __init__(self,
                 suffixes=None,
                 scrub_username=False,
                 scrub_password=True,
                 params_to_scrub=None,
                 redact_char='-',
                 randomize_len=True):

        super(ScrubUrlTransform, self).__init__(suffixes=suffixes,
                                                redact_char=redact_char,
                                                randomize_len=randomize_len)
        self.scrub_username = scrub_username
        self.scrub_password = scrub_password
        self.params_to_scrub = set(map(lambda x: x.lower(), params_to_scrub))

    def in_scrub_fields(self, key):
        if not key:
            # This can happen if the transform is applied to a non-object,
            # like a string.
            return True

        return super(ScrubUrlTransform, self).in_scrub_fields(key)

    def redact(self, url_string):
        _redact = super(ScrubUrlTransform, self).redact

        missing_colon_double_slash = False

        if _starts_with_auth_re.match(url_string):
            missing_colon_double_slash = True
            url_string = '//%s' % url_string

        try:
            url_parts = urlsplit(url_string)
            qs_params = parse_qs(url_parts.query, keep_blank_values=True)
        except:
            # This isn't a URL, return url_string which is a no-op
            # for this transform
            return url_string

        netloc = url_parts.netloc

        # If there's no netloc, give up
        if not netloc:
            return url_string

        for qs_param, vals in iteritems(qs_params):
            if qs_param.lower() in self.params_to_scrub:
                vals2 = map(_redact, vals)
                qs_params[qs_param] = vals2

        scrubbed_qs = urlencode(qs_params, doseq=True)

        if self.scrub_username and url_parts.username:
            redacted_username = _redact(url_parts.username)
            netloc = netloc.replace(url_parts.username, redacted_username)

        if self.scrub_password and url_parts.password:
            redacted_pw = _redact(url_parts.password)
            netloc = netloc.replace(url_parts.password, redacted_pw)

        scrubbed_url = (url_parts.scheme,
                        netloc,
                        url_parts.path,
                        scrubbed_qs,
                        url_parts.fragment)

        scrubbed_url_string = urlunsplit(scrubbed_url)

        if missing_colon_double_slash:
            scrubbed_url_string = scrubbed_url_string.lstrip('://')

        return scrubbed_url_string

    def default(self, o, key=None):
        # Change the default behavior because we are only interested
        # in scrubbing strings.
        if isinstance(o, string_types) or isinstance(o, binary_type):
            return super(ScrubUrlTransform, self).default(o, key=key)

        return o



__all__ = ['ScrubUrlTransform']
