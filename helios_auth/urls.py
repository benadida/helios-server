
"""
Authentication URLs

Ben Adida (ben@adida.net)
"""

from django.conf.urls import url

import url_names
import views
from settings import AUTH_ENABLED_AUTH_SYSTEMS

urlpatterns = [
    # basic static stuff
    url(r'^$', views.index, name=url_names.AUTH_INDEX),
    url(r'^logout$', views.logout, name=url_names.AUTH_LOGOUT),
    url(r'^start/(?P<system_name>.*)$', views.start, name=url_names.AUTH_START),
    # weird facebook constraint for trailing slash
    url(r'^after/$', views.after, name=url_names.AUTH_AFTER),
    url(r'^why$', views.perms_why, name=url_names.AUTH_WHY),
    url(r'^after_intervention$', views.after_intervention, name=url_names.AUTH_AFTER_INTERVENTION),
]

# password auth
if 'password' in AUTH_ENABLED_AUTH_SYSTEMS:
    from auth_systems.password import urlpatterns as password_patterns
    urlpatterns.extend(password_patterns)

# twitter
if 'twitter' in AUTH_ENABLED_AUTH_SYSTEMS:
    from auth_systems.twitter import urlpatterns as twitter_patterns
    urlpatterns.extend(twitter_patterns)

if 'fenix_oauth' in AUTH_ENABLED_AUTH_SYSTEMS:
    from auth_systems.fenix_oauth import urlpatterns as fenix_patterns
    urlpatterns.extend(fenix_patterns)
