# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
from django.contrib import admin

urlpatterns = patterns('',
    (r'^auth/', include('auth.urls')),
    (r'^helios/', include('helios.urls')),
    (r'^', include('single-election.urls')),
)