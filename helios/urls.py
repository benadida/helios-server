# -*- coding: utf-8 -*-
from django.urls import include, path

from . import views, url_names as names

urlpatterns = [
  path('autologin', views.admin_autologin),
  path('testcookie', views.test_cookie, name=names.COOKIE_TEST),
  path('testcookie_2', views.test_cookie_2, name=names.COOKIE_TEST_2),
  path('nocookies', views.nocookies, name=names.COOKIE_NO),
  path('stats/', include('helios.stats_urls')),

  # election shortcut by shortname
  path('e/<str:election_short_name>', views.election_shortcut, name=names.ELECTION_SHORTCUT),
  path('e/<str:election_short_name>/vote', views.election_vote_shortcut, name=names.ELECTION_SHORTCUT_VOTE),

  # vote shortcut
  path('v/<str:vote_tinyhash>', views.castvote_shortcut, name=names.CAST_VOTE_SHORTCUT),

  # vote by hash
  path('vh/<str:vote_hash>', views.castvote_fullhash_shortcut, name=names.CAST_VOTE_FULLHASH_SHORTCUT),
  
  # trustee login
  path('t/<str:election_short_name>/<str:trustee_email>/<str:trustee_secret>', views.trustee_login,
      name=names.TRUSTEE_LOGIN),
  
  # election
  path('elections/params', views.election_params, name=names.ELECTIONS_PARAMS),
  path('elections/verifier', views.election_verifier, name=names.ELECTIONS_VERIFIER),
  path('elections/single_ballot_verifier', views.election_single_ballot_verifier, name=names.ELECTIONS_VERIFIER_SINGLE_BALLOT),
  path('elections/new', views.election_new, name=names.ELECTIONS_NEW),
  path('elections/administered', views.elections_administered, name=names.ELECTIONS_ADMINISTERED),
  path('elections/voted', views.elections_voted, name=names.ELECTIONS_VOTED),
  
  path('elections/<str:election_uuid>', include('helios.election_urls')),
]
