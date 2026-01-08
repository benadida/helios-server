# -*- coding: utf-8 -*-
from django.conf import settings
from django.urls import include, path, re_path
from django.views.static import serve
from helios import views as helios_views

urlpatterns = [
    path('auth/', include('helios_auth.urls')),
    path('helios/', include('helios.urls')),

    re_path(r'booth/(?P<template_name>(templates/)?[a-z\-]+\.html)$', helios_views.booth_template),
    re_path(r'booth/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/heliosbooth'}),

    path('verifier/verify.html', helios_views.verify_template),
    re_path(r'verifier/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/heliosverifier'}),

    re_path(r'static/auth/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/helios_auth/media'}),
    path('static/helios/static_templates/question.html', helios_views.question_template),
    re_path(r'static/helios/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/helios/media'}),
    re_path(r'static/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/server_ui/media'}),

    # Email opt-out/opt-in URLs
    path('optout/', include([
        path('', helios_views.optout_form, name='optout_form'),
        path('success/', helios_views.optout_success, name='optout_success'),
        path('confirm/<str:email>/<str:code>/', helios_views.optout_confirm, name='optout_confirm'),
    ])),
    path('optin/', include([
        path('', helios_views.optin_form, name='optin_form'),
        path('success/', helios_views.optin_success, name='optin_success'),
        path('confirm/<str:email>/<str:code>/', helios_views.optin_confirm, name='optin_confirm'),
    ])),

    path('', include('server_ui.urls')),
]
