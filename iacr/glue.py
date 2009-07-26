"""
Glue some events together 
"""

from django.conf import settings
from django.core.urlresolvers import reverse
import helios.views, helios.signals

import views

def vote_cast_update_status(user, election, cast_vote, **kwargs):
  pass
  
helios.signals.vote_cast.connect(vote_cast_update_status)

def election_tallied(election, **kwargs):
  pass

helios.signals.election_tallied.connect(election_tallied)