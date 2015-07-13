# -*- coding: utf-8 -*-
from django.conf.urls import *
from django.conf import settings

from views import *
from heliosinstitution import views as institution_views

urlpatterns = patterns('',
  (r'^$', home),
  (r'^about$', about),
  (r'^docs$', docs),
  (r'^faq$', faq),
  (r'^privacy$', privacy),
)
