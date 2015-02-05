# -*- coding: utf-8 -*-
from django.conf.urls import *
from django.contrib import admin
from django.conf import settings
from django.views.i18n import javascript_catalog

js_info_dict = {
    'packages': ('helios', 'helios_auth'),
}

admin.autodiscover()

urlpatterns = patterns(
    '',
    (r'^auth/', include('helios_auth.urls')),
    (r'^helios/', include('helios.urls')),  

    (r'^', include('server_ui.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^jsi18n/$', javascript_catalog, js_info_dict),
)

if settings.DEBUG: # otherwise, they should be served by a webserver like apache

    urlpatterns += patterns(
        '',
        # SHOULD BE REPLACED BY APACHE STATIC PATH
        (r'booth/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.ROOT_PATH + '/heliosbooth'}),
        (r'verifier/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.ROOT_PATH + '/heliosverifier'}),

        (r'static/auth/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.ROOT_PATH + '/helios_auth/media'}),
        (r'static/helios/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.ROOT_PATH + '/helios/media'}),
        (r'static/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.ROOT_PATH + '/server_ui/media'})
    )
