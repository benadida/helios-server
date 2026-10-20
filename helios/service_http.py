"""Thread-owned, bounded service connections without persistent login cookies.

Bodies and bearer headers belong to individual calls. Ambiguous POSTs are never
retried by the transport; callers retain their existing durable retry protocol.
"""
from http.cookiejar import DefaultCookiePolicy
from threading import local

import requests
from requests.adapters import HTTPAdapter

_local = local()


class NoCookies(DefaultCookiePolicy):
    def set_ok(self, cookie, request):
        return False


def post(url, **kwargs):
    if not hasattr(_local, 'session'):
        session = requests.Session()
        session.cookies.set_policy(NoCookies())
        for scheme in ('https://', 'http://'):
            session.mount(scheme, HTTPAdapter(pool_connections=2, pool_maxsize=1,
                                             pool_block=True, max_retries=0))
        _local.session = session
    return _local.session.post(url, **kwargs)
