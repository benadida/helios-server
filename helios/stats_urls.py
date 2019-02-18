"""
Helios URLs for Election related stuff

Ben Adida (ben@adida.net)
"""

from django.conf.urls import url

from helios.stats_views import (home, force_queue, elections, recent_problem_elections, recent_votes)

urlpatterns = [
    url(r'^$', home),
    url(r'^force-queue$', force_queue),
    url(r'^elections$', elections),
    url(r'^problem-elections$', recent_problem_elections),
    url(r'^recent-votes$', recent_votes),
]
