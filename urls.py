# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
from django.conf import settings

from zeus.views import admin

SERVER_PREFIX = getattr(settings, 'SERVER_PREFIX', '')
if SERVER_PREFIX:
    SERVER_PREFIX = SERVER_PREFIX.rstrip('/') + '/'

app_patterns = patterns('')

auth_urls = patterns('zeus.views.auth',
    url(r'^auth/logout', 'logout', name='logout'),
    url(r'^auth/login', 'password_login_view', name='login'),
    url(r'^auth/change_password', 'change_password', name='change_password'),
    url(r'^voter-login$', 'voter_login', name="voter_login"),
    url(r'^auth/oauth2$', 'oauth2_login', name="oauth2_login"),
    url(r'^auth/jwt$', 'jwt_login', name="jwt_login"),
    url(r'^auth/shibboleth/(?P<endpoint>.*)$', 'shibboleth_login', name="shibboleth_login"),
)

admin_urls = patterns('zeus.views.admin',
    url(r'^$', admin.HomeView.as_view(), name='admin_home'),
    url(r'^reports$', 'elections_report', name='elections_report'),
    url(r'^reports/csv$', 'elections_report_csv', name='elections_report_csv'),
)

app_patterns += patterns(
    '',
    (r'^', include('zeus.urls.site')),
    (r'^elections/', include('zeus.urls.election')),
    (r'^auth/', include(auth_urls)),
    (r'^admin/', include(admin_urls)),
    url(r'^get-randomness/', 'zeus.views.shared.get_randomness',
        name="get_randomness"),
    url(r'^i18n/js', 'django.views.i18n.javascript_catalog',
        name='js_messages', kwargs={'packages': None}),
    (r'^i18n/setlang', 'zeus.views.site.setlang'),
    (r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^account_administration/', include('account_administration.urls')),
)

urlpatterns = patterns(
    '',
    (r'^' + SERVER_PREFIX, include(app_patterns)),
)

#SHOULD BE REPLACED BY APACHE STATIC PATH
if getattr(settings, 'DEBUG', False) or getattr(settings, 'ZEUS_SERVE_STATIC', False):
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

    urlpatterns += static_urls

handler500 = 'zeus.views.site.handler500'
handler400 = 'zeus.views.site.handler400'
handler403 = 'zeus.views.site.handler403'
handler404 = 'zeus.views.site.handler404'
