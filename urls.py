# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
from django.conf import settings

SERVER_PREFIX = getattr(settings, 'SERVER_PREFIX', '')
if SERVER_PREFIX:
    SERVER_PREFIX = SERVER_PREFIX.rstrip('/') + '/'

app_patterns = patterns('')

auth_urls = patterns('zeus.views.auth',
    url(r'^auth/logout', 'logout', name='logout'),
    url(r'^auth/login', 'password_login_view', name='login'),
)

static_urls = patterns('',
    (r'booth/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root' : settings.BOOTH_STATIC_PATH
    }),
    (r'static/zeus/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root' : settings.ROOT_PATH + '/zeus/static/zeus'
    }),
    (r'static/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root' : settings.ROOT_PATH + '/server_ui/media'
    }),
)

admin_urls = patterns('zeus.views.admin',
    url(r'^$', 'home', name='admin_home'),
)

app_patterns += patterns(
    '',
    (r'^', include('zeus.urls.site')),
    (r'^elections/', include('zeus.urls.election')),
    (r'^auth/', include(auth_urls)),
    (r'^admin/', include(admin_urls)),
    url(r'^get-randomness/', 'zeus.views.shared.get_randomness',
        name="get_randomness"),
)

# SHOULD BE REPLACED BY APACHE STATIC PATH
app_patterns += static_urls

urlpatterns = patterns(
    '',
    (r'^' + SERVER_PREFIX, include(app_patterns)),
)
