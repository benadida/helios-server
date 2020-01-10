"""
Helios Signals

Effectively callbacks that other apps can wait and be notified about
"""

import django.dispatch

# when an election is created
election_created = django.dispatch.Signal(providing_args=["election"])

# when a vote is cast
vote_cast = django.dispatch.Signal(providing_args=["user", "voter", "election", "cast_vote"])

# when an election is tallied
election_tallied = django.dispatch.Signal(providing_args=["election"])