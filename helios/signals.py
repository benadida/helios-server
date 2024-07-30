"""
Helios Signals

Effectively callbacks that other apps can wait and be notified about.

Named arguments for each signal:
    election_created : "election"
    vote_cast : "user", "voter", "election", "cast_vote"
    election_tallied : "election"
"""

import django.dispatch

# when an election is created
election_created = django.dispatch.Signal()

# when a vote is cast
vote_cast = django.dispatch.Signal()

# when an election is tallied
election_tallied = django.dispatch.Signal()