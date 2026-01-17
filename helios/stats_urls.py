"""
Helios URLs for Election related stuff

Ben Adida (ben@adida.net)
"""

from django.urls import path

from helios.stats_views import (home, force_queue, elections, recent_problem_elections, recent_votes, user_search)
import helios.stats_url_names as names

urlpatterns = [
    path('', home, name=names.STATS_HOME),
    path('force-queue', force_queue, name=names.STATS_FORCE_QUEUE),
    path('elections', elections, name=names.STATS_ELECTIONS),
    path('problem-elections', recent_problem_elections, name=names.STATS_ELECTIONS_PROBLEMS),
    path('recent-votes', recent_votes, name=names.STATS_RECENT_VOTES),
    path('user-search', user_search, name=names.STATS_USER_SEARCH),
]
