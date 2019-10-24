# -*- coding: utf-8 -*-
from django.urls import re_path
from server_ui.views import home, about, docs, faq, privacy, save_vote_handler

urlpatterns = [
  re_path(r'^$', home, name='home'),
  re_path(r'^about$', about, name='about'),
  re_path(r'^docs$', docs, name='docs'),
  re_path(r'^faq$', faq, name='faq'),
  re_path(r'^privacy$', privacy, name='privacy'),
    
  # cloud task handlers
  # re_path(r'^save_vote_handler$', save_vote_handler, name='save-vote-handler'),
]
