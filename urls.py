# -*- coding: utf-8 -*-
from django.conf import settings
from django.conf.urls import url, include
from django.views.static import serve

urlpatterns = [
    url(r'^auth/', include('helios_auth.urls')),
    url(r'^helios/', include('helios.urls')),

    # SHOULD BE REPLACED BY APACHE STATIC PATH
    url(r'booth/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/heliosbooth'}),
    url(r'verifier/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/heliosverifier'}),

    url(r'static/auth/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/helios_auth/media'}),
    url(r'static/helios/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/helios/media'}),
    url(r'static/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/server_ui/media'}),

    url(r'^', include('server_ui.urls')),
]
