# -*- coding: utf-8 -*-
from django.conf import settings
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('auth/', include('helios_auth.urls')),
    path('helios/', include('helios.urls')),

    # SHOULD BE REPLACED BY APACHE STATIC PATH
    re_path(r'booth/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/heliosbooth'}),
    re_path(r'verifier/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/heliosverifier'}),

    re_path(r'static/auth/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/helios_auth/media'}),
    re_path(r'static/helios/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/helios/media'}),
    re_path(r'static/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/server_ui/media'}),

    path('', include('server_ui.urls')),
]
