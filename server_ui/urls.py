# -*- coding: utf-8 -*-
from django.conf.urls import *
from django.conf import settings

from views import *
from heliosinstitution import views as institution_views

urlpatterns = patterns('',
  (r'^about$', about),
  (r'^docs$', docs),
  (r'^faq$', faq),
  (r'^privacy$', privacy),
)

if settings.AUTH_DEFAULT_AUTH_SYSTEM == 'shibboleth':
	urlpatterns += patterns('',
		(r'^$', institution_views.home),
	)
else:
	urlpatterns += patterns('',
		(r'^$', home),
	)
