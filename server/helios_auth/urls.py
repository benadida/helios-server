"""
Authentication URLs

Ben Adida (ben@adida.net)
"""

from django.conf.urls import url

from . import views
from settings import AUTH_ENABLED_AUTH_SYSTEMS

urlpatterns = [
    # basic static stuff
    url(r"^$", views.index),
    url(r"^logout$", views.logout),
    url(r"^start/(?P<system_name>.*)$", views.start),
    # weird facebook constraint for trailing slash
    url(r"^after/$", views.after),
    url(r"^why$", views.perms_why),
    url(r"^after_intervention$", views.after_intervention),
]

# password auth
if "password" in AUTH_ENABLED_AUTH_SYSTEMS:
    from .auth_systems.password import password_login_view, password_forgotten_view

    urlpatterns.append(url(r"^password/login", password_login_view))
    urlpatterns.append(url(r"^password/forgot", password_forgotten_view))

# twitter
if "twitter" in AUTH_ENABLED_AUTH_SYSTEMS:
    from .auth_systems.twitter import follow_view

    urlpatterns.append(url(r"^twitter/follow", follow_view))
