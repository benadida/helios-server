# -*- coding: utf-8 -*-
from django.conf.urls import patterns

from views import home, about, docs, faq, privacy

urlpatterns = patterns('',
  (r'^$', home),
  (r'^about$', about),
  (r'^docs$', docs),
  (r'^faq$', faq),
  (r'^privacy$', privacy),
)
