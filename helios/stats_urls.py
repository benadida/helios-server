"""
Helios URLs for Election related stuff

Ben Adida (ben@adida.net)
"""

from django.conf.urls import *

from helios.stats_views import *

urlpatterns = patterns(
    '',
    (r'^$', home),
    (r'^force-queue$', force_queue),
    (r'^elections$', elections),
    (r'^problem-elections$', recent_problem_elections),
    (r'^recent-votes$', recent_votes),
    (r'^admin-actions$', admin_actions),
)
