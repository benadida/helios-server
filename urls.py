# -*- coding: utf-8 -*-
from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin
from django.views.static import serve
from django.views.i18n import javascript_catalog

js_info_dict = {
    'packages': ('helios', 'helios_auth'),
}

admin.autodiscover()

urlpatterns = [
    url(r'^auth/', include('helios_auth.urls')),
    url(r'^helios/', include('helios.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^jsi18n/$', javascript_catalog, js_info_dict),
]

if settings.AUTH_DEFAULT_AUTH_SYSTEM == 'shibboleth':
    urlpatterns += [
        url(r'^', include('heliosinstitution.urls')),
    ]
else:
    urlpatterns += [
        url(r'^', include('server_ui.urls')),
    ]

if settings.DEBUG:  # otherwise, they should be served by a webserver like apache
    urlpatterns += [
        # SHOULD BE REPLACED BY APACHE STATIC PATH
        url(r'booth/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/heliosbooth'}),
        url(r'verifier/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/heliosverifier'}),

        url(r'static/auth/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/helios_auth/media'}),
        url(r'static/helios/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/helios/media'}),
        url(r'static/heliosinstitution/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/heliosinstitution/media'}),
        url(r'static/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/server_ui/media'}),
    ]
