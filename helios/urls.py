# -*- coding: utf-8 -*-
from django.conf.urls import url, include

from . import views, url_names as names

urlpatterns = [
  url(r'^autologin$', views.admin_autologin),
  url(r'^testcookie$', views.test_cookie, name=names.COOKIE_TEST),
  url(r'^testcookie_2$', views.test_cookie_2, name=names.COOKIE_TEST_2),
  url(r'^nocookies$', views.nocookies, name=names.COOKIE_NO),
  url(r'^stats/', include('helios.stats_urls')),

  # election shortcut by shortname
  url(r'^e/(?P<election_short_name>[^/]+)$', views.election_shortcut, name=names.ELECTION_SHORTCUT),
  url(r'^e/(?P<election_short_name>[^/]+)/vote$', views.election_vote_shortcut, name=names.ELECTION_SHORTCUT_VOTE),

  # vote shortcut
  url(r'^v/(?P<vote_tinyhash>[^/]+)$', views.castvote_shortcut, name=names.CAST_VOTE_SHORTCUT),

  # vote by hash
  url(r'^vh/(?P<vote_hash>[^/]+)$', views.castvote_fullhash_shortcut, name=names.CAST_VOTE_FULLHASH_SHORTCUT),
  
  # trustee login
  url(r'^t/(?P<election_short_name>[^/]+)/(?P<trustee_email>[^/]+)/(?P<trustee_secret>[^/]+)$', views.trustee_login,
      name=names.TRUSTEE_LOGIN),
  
  # election
  url(r'^elections/params$', views.election_params, name=names.ELECTIONS_PARAMS),
  url(r'^elections/verifier$', views.election_verifier, name=names.ELECTIONS_VERIFIER),
  url(r'^elections/single_ballot_verifier$', views.election_single_ballot_verifier, name=names.ELECTIONS_VERIFIER_SINGLE_BALLOT),
  url(r'^elections/new$', views.election_new, name=names.ELECTIONS_NEW),
  url(r'^elections/administered$', views.elections_administered, name=names.ELECTIONS_ADMINISTERED),
  url(r'^elections/voted$', views.elections_voted, name=names.ELECTIONS_VOTED),
  
  url(r'^elections/(?P<election_uuid>[^/]+)', include('helios.election_urls')),
]
