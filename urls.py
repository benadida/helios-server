# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
from django.contrib import admin

urlpatterns = patterns('',
    (r'^auth/', include('auth.urls')),
    (r'^helios/', include('helios.urls')),
    (r'^', include('votwee.urls')),

    # static hack -- production should bypass this route
    #(r'^static/helios/(?P<path>.*)$', 'django.views.static.serve',
    #        {'document_root': '/web/votwee/helios/media/helios/'}),
)