# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *

from views import *

urlpatterns = patterns('',
                       (r'^$', home),
                       (r'^about$', about),
                       (r'^docs$', docs),
                       (r'^faq$', faq),
                       (r'^privacy$', privacy),
                       )
