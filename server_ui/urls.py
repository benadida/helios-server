# -*- coding: utf-8 -*-
from django.conf.urls import *

from views import *

urlpatterns = patterns('',
  (r'^$', home),
  (r'^about$', about),
  (r'^docs$', docs),
  (r'^faq$', faq),
  (r'^privacy$', privacy),
)
