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
    (r'^logout$', logout),
    (r'^start/(?P<system_name>.*)$', start),
    (r'^after$', after),
    (r'^after_intervention$', after_intervention),
    
    ## should make the following modular

    # password auth
    (r'^password/login', password_login_view),
    (r'^password/forgot', password_forgotten_view),

    # twitter
    (r'^twitter/follow', follow_view),
)
