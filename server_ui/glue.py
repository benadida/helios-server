"""
Glue some events together
"""

from django.conf import settings
from django.core.urlresolvers import reverse
from django.conf import settings
import helios.views, helios.signals
import views
from django.utils.translation import ugettext_lazy as _

def vote_cast_send_message(user, voter, election, cast_vote, **kwargs):
  ## FIXME: this doesn't work for voters that are not also users
  # prepare the message
  subject = _("%(election_name)s - vote cast") % {'election_name': election.name}

  body = _(u"""
You have successfully cast a vote in

  %(election_name)s

you can find your encrypted vote attached in this mail.
""") % {'election_name': election.name }

  # send it via the notification system associated with the auth system
  attachments = [('vote.json', voter.vote.toJSON(), 'text/plain')]
  user.send_message(subject, body, attachments=attachments)

helios.signals.vote_cast.connect(vote_cast_send_message)

def election_tallied(election, **kwargs):
  pass

helios.signals.election_tallied.connect(election_tallied)
