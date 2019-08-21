"""
Glue some events together 
"""

from django.conf import settings
from django.core.urlresolvers import reverse
from django.conf import settings
import helios.views, helios.signals

import views

def vote_cast_send_message(user, voter, election, cast_vote, **kwargs):
  ## FIXME: this doesn't work for voters that are not also users
  # prepare the message
  subject = "%s - vote cast" % election.name
  
  body = """
You have successfully cast a vote in

  %s
  
Your ballot is archived at:

  %s
""" % (election.name, helios.views.get_castvote_url(cast_vote))
  
  if election.use_voter_aliases:
    body += """

This election uses voter aliases to protect your privacy.
Your voter alias is : %s    
""" % voter.alias

  body += """

--
%s
""" % settings.SITE_TITLE  
  
  # send it via the notification system associated with the auth system
  user.send_message(subject, body)

helios.signals.vote_cast.connect(vote_cast_send_message)

def election_tallied(election, **kwargs):
  pass

helios.signals.election_tallied.connect(election_tallied)
