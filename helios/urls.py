# -*- coding: utf-8 -*-
from django.conf.urls import url, include

from views import *

urlpatterns = [
  url(r'^autologin$', admin_autologin),
  url(r'^testcookie$', test_cookie),
  url(r'^testcookie_2$', test_cookie_2),
  url(r'^nocookies$', nocookies),
  url(r'^stats/', include('helios.stats_urls')),

  # election shortcut by shortname
  url(r'^e/(?P<election_short_name>[^/]+)$', election_shortcut),
  url(r'^e/(?P<election_short_name>[^/]+)/vote$', election_vote_shortcut),

  # vote shortcut
  url(r'^v/(?P<vote_tinyhash>[^/]+)$', castvote_shortcut),
  
  # trustee login
  url(r'^t/(?P<election_short_name>[^/]+)/(?P<trustee_email>[^/]+)/(?P<trustee_secret>[^/]+)$', trustee_login),
  
  # election
  url(r'^elections/params$', election_params),
  url(r'^elections/verifier$', election_verifier),
  url(r'^elections/single_ballot_verifier$', election_single_ballot_verifier),
  url(r'^elections/new$', election_new),
  url(r'^elections/administered$', elections_administered),
  url(r'^elections/voted$', elections_voted),
  
  url(r'^elections/(?P<election_uuid>[^/]+)', include('helios.election_urls')),

  url(r'^heliosinstitution/', include('heliosinstitution.urls')),
]
