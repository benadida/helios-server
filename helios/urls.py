# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
from django.conf import settings
from views import *

urlpatterns = None

urlpatterns = patterns('',
  (r'^$', home),

  # trustee login
  url(r'^t/(?P<election_uuid>[^/]+)/(?P<trustee_email>[^/]+)/(?P<trustee_secret>[^/]+)$',
  'zeus.views.trustee.login', name="election_trustee_login"),

  # election
  (r'^elections/params$', election_params),
  url(r'^elections/new$', 'zeus.views.election.add_or_update',
      name='election_create'),
  url(r'^elections/(?P<election_uuid>[^/]+)', include('zeus.urls.election')),
)


