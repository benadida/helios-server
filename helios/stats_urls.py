"""
Helios URLs for Election related stuff

Ben Adida (ben@adida.net)
"""

from django.conf.urls import *

from helios.stats_views import *

urlpatterns = [
    url(r'^$', home, name='stats-view-home'),
    url(r'^force-queue$', force_queue, name='stats-view-force-queue'),
    url(r'^elections$', elections, name='stats-view-elections'),
    url(r'^problem-elections$', recent_problem_elections, name='stats-view-recent-problem-elections'),
    url(r'^recent-votes$', recent_votes,name='stats-view-recent-votes'),
]
