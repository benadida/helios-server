# -*- coding: utf-8 -*-
from django.urls import include, re_path

from .views import *

urlpatterns = [
  re_path(r'^autologin$', admin_autologin, name='admin_autologin'),
  re_path(r'^testcookie$', test_cookie, name='test_cookie'),
  re_path(r'^testcookie_2$', test_cookie_2, name='test_cookie_2'),
  re_path(r'^nocookies$', nocookies, name='nocookies'),
  re_path(r'^stats/', include('helios.stats_urls')),

  # election shortcut by shortname
  re_path(r'^e/(?P<election_short_name>[^/]+)$', election_shortcut, name='election-shortcut'),
  re_path(r'^e/(?P<election_short_name>[^/]+)/vote$', election_vote_shortcut, name='election-vote-shortcut'),

  # vote shortcut
  re_path(r'^v/(?P<vote_tinyhash>[^/]+)$', castvote_shortcut, name='castvote-shortcut'),
  
  # trustee login
  re_path(r'^t/(?P<election_short_name>[^/]+)/(?P<trustee_email>[^/]+)/(?P<trustee_secret>[^/]+)$', trustee_login, name='trustee-login'),
  
  # election
  re_path(r'^elections/params$', election_params, name='election-params'),
  re_path(r'^elections/verifier$', election_verifier, name='election-verifier'),
  re_path(r'^elections/single_ballot_verifier$', election_single_ballot_verifier, name='election-single-ballot_verifier'),
  re_path(r'^elections/new$', election_new, name='election-new'),
  re_path(r'^elections/administered$', elections_administered, name='elections-administered'),
  re_path(r'^elections/voted$', elections_voted, name='elections-voted'),
  
  re_path(r'^elections/(?P<election_uuid>[^/]+)/', include('helios.election_urls')),

]


