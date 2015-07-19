# -*- coding: utf-8 -*-
from django.conf.urls import *
from django.contrib import admin
from django.conf import settings

urlpatterns = patterns('',
    (r'^helios_auth/', include('helios_auth.urls')),
    (r'^helios/', include('helios.urls')),

    # SHOULD BE REPLACED BY APACHE STATIC PATH
    (r'booth/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.ROOT_PATH + '/helios_booth'}),
    (r'verifier/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.ROOT_PATH + '/helios_verifier'}),

    (r'static/helios_auth/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.ROOT_PATH + '/helios_auth/media'}),
    (r'static/helios/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.ROOT_PATH + '/helios/media'}),
    (r'static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.ROOT_PATH + '/server_ui/media'}),

    (r'^', include('server_ui.urls')),
)
