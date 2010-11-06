"""
Helios URLs for Election related stuff

Ben Adida (ben@adida.net)
"""

from django.conf.urls.defaults import *

from helios.stats_views import *

urlpatterns = patterns(
    '',
    (r'^$', home),
    (r'^elections$', elections),
)
