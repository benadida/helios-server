# -*- coding: utf-8 -*-
from django.conf.urls import url

from server_ui.views import home, about, docs, faq, privacy

urlpatterns = [
  url(r'^$', home),
  url(r'^about$', about),
  url(r'^docs$', docs),
  url(r'^faq$', faq),
  url(r'^privacy$', privacy),
]
