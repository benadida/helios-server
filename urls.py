# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
from django.conf import settings

urlpatterns = patterns('')

for slug, uuid in getattr(settings, 'ZEUS_ALTERNATIVE_LOGIN_ELECTIONS', {}).iteritems():
  urlpatterns += patterns('',
    url(r'%s/' % slug, 'zeus.views.election_email_login', kwargs={'uuid': uuid}),
  )

urlpatterns += patterns(
    '',
    (r'^$', 'zeus.views.home'),
    (r'^admin/$', 'server_ui.views.home'),
    (r'^faqs/$', 'zeus.views.faqs_voter'),
    (r'^faqs/voter/$', 'zeus.views.faqs_voter'),
    (r'^faqs/trustee/$', 'zeus.views.faqs_trustee'),
    (r'^resources/$', 'zeus.views.resources'),
    (r'^stats/$', 'zeus.views.stats'),
    (r'^auth/', include('heliosauth.urls')),
    (r'^helios/', include('helios.urls')),
    url(r'voter_email/$', 'zeus.views.election_email_show', name='election_email_show'),


    # SHOULD BE REPLACED BY APACHE STATIC PATH
    (r'booth/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.BOOTH_STATIC_PATH}),
    (r'static/auth/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.ROOT_PATH + '/heliosauth/media'}),
    (r'static/helios/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.ROOT_PATH + '/helios/media'}),
    (r'static/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.ROOT_PATH + '/server_ui/media'}),

    (r'^', include('server_ui.urls')),
)


if settings.DEBUG:
    from helios.devutils import quick_start_election
    urlpatterns += patterns(
        (r'^helios/test-create', quick_start_election),
    )
