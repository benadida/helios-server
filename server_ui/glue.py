"""
Glue some events together
"""

from django.conf import settings
from django.core.urlresolvers import reverse
from django.conf import settings
import helios.views, helios.signals
import views
from django.utils.translation import ugettext_lazy as _
from django.core.mail import send_mail, EmailMessage

def vote_cast_send_message(user, voter, election, signature, **kwargs):
  ## FIXME: this doesn't work for voters that are not also users
  # prepare the message
  subject = _("%(election_name)s - vote cast") % {'election_name': election.name}

  body = _(u"""
You have successfully cast a vote in

  %(election_name)s

you can find your encrypted vote attached in this mail.
""") % {'election_name': election.name }

  # send it via the notification system associated with the auth system
  attachments = [('vote.signature', signature['m'], 'text/plain')]
  message = EmailMessage(subject, body, settings.SERVER_EMAIL, ["%s <%s>" % (voter.voter_name,
                                                                voter.voter_email)])
  for attachment in attachments:
      message.attach(*attachment)

  message.send(fail_silently=True)

helios.signals.vote_cast.connect(vote_cast_send_message)

def election_tallied(election, **kwargs):
  pass

helios.signals.election_tallied.connect(election_tallied)
