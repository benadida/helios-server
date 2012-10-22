"""
Celery queued tasks for Helios

2010-08-01
ben@adida.net
"""

import traceback
import signals
import copy
import datetime
import json
import urllib, urllib2

from celery.decorators import task

from helios.models import *
from helios.view_utils import render_template_raw

from django.utils.translation import ugettext_lazy as _
from django.core.mail import send_mail, EmailMessage

@task()
def cast_vote_verify_and_store(cast_vote_id, status_update_message=None, **kwargs):
    cast_vote = CastVote.objects.get(id = cast_vote_id)
    result = cast_vote.verify_and_store()

    voter = cast_vote.voter
    election = voter.election
    user = voter.user

    if result:
        # send the signal
        signals.vote_cast.send(sender=election, election=election, user=user, voter=voter, cast_vote=cast_vote)

        if status_update_message and user.can_update_status():
            from views import get_election_url

            user.update_status(status_update_message)
    else:
        logger = cast_vote_verify_and_store.get_logger(**kwargs)
        logger.error("Failed to verify and store %d" % cast_vote_id)

@task()
def voters_email(election_id, subject_template, body_template, extra_vars={},
                 voter_constraints_include=None, voter_constraints_exclude=None):
    """
    voter_constraints_include are conditions on including voters
    voter_constraints_exclude are conditions on excluding voters
    """
    election = Election.objects.get(id = election_id)

    # select the right list of voters
    voters = election.voter_set.all()
    if voter_constraints_include:
        voters = voters.filter(**voter_constraints_include)
    if voter_constraints_exclude:
        voters = voters.exclude(**voter_constraints_exclude)

    for voter in voters:
        single_voter_email.delay(voter.uuid, subject_template, body_template, extra_vars)

@task()
def voters_notify(election_id, notification_template, extra_vars={}):
    election = Election.objects.get(id = election_id)
    for voter in election.voter_set.all():
        single_voter_notify.delay(voter.uuid, notification_template, extra_vars)

@task(rate_limit=getattr(settings, 'HELIOS_VOTER_EMAIL_RATE', '20/m'))
def single_voter_email(voter_uuid, subject_template, body_template,
                       extra_vars={}, update_date=True):
    voter = Voter.objects.get(uuid = voter_uuid)

    the_vars = copy.copy(extra_vars)
    the_vars.update({'voter' : voter})

    subject = render_template_raw(None, subject_template, the_vars)
    body = render_template_raw(None, body_template, the_vars)

    if update_date:
      voter.last_email_send_at = datetime.datetime.now()
      voter.save()

    voter.user.send_message(subject, body)

@task()
def single_voter_notify(voter_uuid, notification_template, extra_vars={}):
    voter = Voter.objects.get(uuid = voter_uuid)

    the_vars = copy.copy(extra_vars)
    the_vars.update({'voter' : voter})

    notification = render_template_raw(None, notification_template, the_vars)

    voter.user.send_notification(notification)

@task()
def election_compute_tally(election_id):
    election = Election.objects.get(id = election_id)
    try:
        election.zeus_election.validate_voting()
    except:
        election.tallying_started_at = None
        election.save()
        return
    election_notify_admin.delay(election_id=election_id, subject="Voting validated", "")
    election.compute_tally()
    election_notify_admin.delay(election_id=election_id, subject="Mixing finished", "")
    bad_mixnet = election.bad_mixnet()
    if bad_mixnet:
        election_notify_admin.delay(election_id = election_id,
                                subject = "encrypted tally failed to compute",
                                body = """
Error occured while mixing. Mixnet data where cleared.

Mixnet: %s

error: %s
""" % (bad_mixnet.name, bad_mixnet.mix_error))
        bad_mixnet.reset_mixing()
        if bad_mixnet.mix_order == 0:
          election.tallying_started_at = None

        election.save()
        return

    if election.mixing_finished and election.has_helios_trustee():
        election_notify_admin.delay(election_id = election_id,
                                subject = "encrypted tally computed",
                                body = """
The encrypted tally for election %s has been computed.

--
Zeus
""" % election.name)
        tally_helios_decrypt.delay(election_id=election.id)
    else:
        election_compute_tally.delay(election_id=election_id)

@task()
def add_trustee_factors(election_id, trustee_id, factors, proofs):
  election = Election.objects.get(pk=election_id)
  trustee = election.trustee_set.get(pk=trustee_id)
  try:
    election.add_trustee_factors(trustee, factors, proofs)
  except Exception, e:
    election_notify_admin.delay(election_id = election_id,
                                subject = 'Error uploading factors and proofs',
                                body = """
%s

%s
--
Zeus
""" % (election.name, traceback.format_exc()))
    try:
      trustee.send_url_via_mail(msg=_('Invalid partial decryption send. Please try again.'))
    except:
      pass

@task()
def tally_decrypt(election_id):
    election = Election.objects.get(id=election_id)
    if not election.ready_for_decryption_combination():
        raise Exception("Not all trustee factors uploaded")

    election = Election.objects.get(id = election_id)
    election.zeus_election.decrypt_ballots()

    election = Election.objects.get(id=election_id)
    try:
        election.store_zeus_proofs()
    except:
        election_notify_admin.delay(election_id, "Failed to store zeus proofs",
                                   traceback.format_exc())
    try:
        election.post_ecounting()
    except:
        election_notify_admin.delay(election_id, "Failed to post to ecounting",
                                   traceback.format_exc())
    election_notify_admin.delay(election_id = election_id,
                                subject = 'Election Decrypt',
                                body = """
Result decrypted for election %s.
--
Zeus
""" % election.name)


@task()
def tally_helios_decrypt(election_id):
    election = Election.objects.get(id = election_id)
    if not election.mixing_finished:
      raise Exception("Mixing not finished cannot decrypt")

    #election.zeus_election.validate_mixing()
    election.helios_trustee_decrypt()

    for t in election.trustee_set.filter(secret_key__isnull=True):
      t.send_url_via_mail()

    election_notify_admin.delay(election_id = election_id,
                                subject = 'Helios Decrypt',
                                body = """
Zeus has decrypted its portion of the tally
for election %s.

--
Zeus
""" % election.name)

@task()
def voter_file_process(voter_file_id):
    voter_file = VoterFile.objects.get(id = voter_file_id)
    voter_file.process()
    election_notify_admin.delay(election_id = voter_file.election.id,
                                subject = 'voter file processed',
                                body = """
Your voter file upload for election %s
has been processed.

%s voters have been created.

--
Zeus
""" % (voter_file.election.name, voter_file.num_voters))

@task()
def election_notify_admin(election_id, subject, body=""):
    election = Election.objects.get(id = election_id)
    #for admin in election.admins.all():
      #admin.send_message(subject, body)
    for admin, admin_email in settings.ELECTION_ADMINS:
        subject = "[%s] %s" % (election.uuid, subject)
        message = EmailMessage(subject,
                               body,
                               settings.SERVER_EMAIL,
                               ["%s <%s>" % (admin, admin_email)])
        message.send(fail_silently=False)


@task()
def send_cast_vote_email(election, voter, signature):
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

  message.send(fail_silently=False)

@task()
def election_post_ecounting(election_id, user=None):
    e = Election.objects.get(pk=election_id)
    ecounting_data = e.ecounting_dict()
    ecounting_data.update(getattr(settings, 'ECOUNTING_SECRET', ''))
    ecounting_data['username'] = user

    data = {
        'json': json.dumps(ecounting_data, ensure_ascii=1)
    }

    values = urllib.urlencode(data)
    url = getattr(settings, 'ECOUNTING_POST_URL', None)

    if not url:
      return

    req = urllib2.Request(url, values)
    response = urllib2.urlopen(req)
    ecount_response = json.loads(response.read())
    if ecount_response['success']:
        e.ecounting_request_send = datetime.datetime.now()
        e.save()


