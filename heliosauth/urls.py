"""
Authentication URLs

Ben Adida (ben@adida.net)
"""

from django.conf.urls.defaults import *

from views import *
from auth_systems.password import password_login_view, password_forgotten_view
from auth_systems.twitter import follow_view

urlpatterns = patterns('',
    # basic static stuff
    (r'^$', index),
    (r'^change_password$', change_password),
    (r'^after/$', after),
    (r'^after_intervention$', after_intervention)
)
