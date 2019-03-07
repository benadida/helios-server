"""
Helios URLs for Election related stuff

Ben Adida (ben@adida.net)
"""

from django.conf.urls import url

from helios.stats_views import (home, force_queue, elections, recent_problem_elections, recent_votes)
import helios.stats_url_names as names

urlpatterns = [
    url(r'^$', home, name=names.STATS_HOME),
    url(r'^force-queue$', force_queue, name=names.STATS_FORCE_QUEUE),
    url(r'^elections$', elections, name=names.STATS_ELECTIONS),
    url(r'^problem-elections$', recent_problem_elections, name=names.STATS_ELECTIONS_PROBLEMS),
    url(r'^recent-votes$', recent_votes, name=names.STATS_RECENT_VOTES),
]
