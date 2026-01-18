"""
Celery queued tasks for Helios

2010-08-01
ben@adida.net
"""
import copy
import datetime
from celery import shared_task
from celery.utils.log import get_logger
from django.conf import settings
from django.urls import reverse
from urllib.parse import urlparse

from . import signals
from . import utils
from .models import CastVote, Election, Voter, VoterFile, EmailOptOut
from .view_utils import render_template_raw


@shared_task
def cast_vote_verify_and_store(cast_vote_id, status_update_message=None, **kwargs):
    cast_vote = CastVote.objects.get(id=cast_vote_id)
    result = cast_vote.verify_and_store()

    voter = cast_vote.voter
    election = voter.election
    user = voter.get_user()

    if result:
        # send the signal
        signals.vote_cast.send(sender=election, election=election, user=user, voter=voter, cast_vote=cast_vote)

        if status_update_message and user.can_update_status():
            user.update_status(status_update_message)
    else:
        logger = get_logger(cast_vote_verify_and_store.__name__)
        logger.error("Failed to verify and store %d" % cast_vote_id)


@shared_task
def voters_email(election_id, subject_template, body_template, extra_vars={},
                 voter_constraints_include=None, voter_constraints_exclude=None):
    """
    voter_constraints_include are conditions on including voters
    voter_constraints_exclude are conditions on excluding voters
    """
    election = Election.objects.get(id=election_id)

    # select the right list of voters
    voters = election.voter_set.all()
    if voter_constraints_include:
        voters = voters.filter(**voter_constraints_include)
    if voter_constraints_exclude:
        voters = voters.exclude(**voter_constraints_exclude)

    for voter in voters:
        single_voter_email.delay(voter.uuid, subject_template, body_template, extra_vars)


@shared_task
def voters_notify(election_id, notification_template, extra_vars={}):
    election = Election.objects.get(id=election_id)
    for voter in election.voter_set.all():
        single_voter_notify.delay(voter.uuid, notification_template, extra_vars)


@shared_task
def single_voter_email(voter_uuid, subject_template, body_template, extra_vars={}):
    voter = Voter.objects.get(uuid=voter_uuid)
    
    # Check if voter email is opted out
    voter_email = voter.voter_email or (voter.user and voter.user.user_id)
    if voter_email and EmailOptOut.is_opted_out(voter_email):
        logger = get_logger(single_voter_email.__name__)
        logger.info(f"Skipping email to opted-out voter {voter.uuid}")
        return

    the_vars = copy.copy(extra_vars)
    the_vars.update({'election': voter.election})
    the_vars.update({'voter': voter})
    
    # Add unsubscribe link to email context
    if voter_email:
        unsubscribe_code = utils.generate_email_confirmation_code(voter_email, 'optout')
        unsubscribe_path = reverse('optout_confirm', kwargs={'email': voter_email, 'code': unsubscribe_code})
        unsubscribe_url = f"{settings.URL_HOST}{unsubscribe_path}"
        
        the_vars.update({
            'unsubscribe_url': unsubscribe_url,
            'unsubscribe_code': unsubscribe_code
        })

    subject = render_template_raw(None, subject_template, the_vars)
    body = render_template_raw(None, body_template, the_vars)

    voter.send_message(subject, body)


@shared_task
def single_voter_notify(voter_uuid, notification_template, extra_vars={}):
    voter = Voter.objects.get(uuid=voter_uuid)

    the_vars = copy.copy(extra_vars)
    the_vars.update({'voter': voter})

    notification = render_template_raw(None, notification_template, the_vars)

    voter.send_notification(notification)


@shared_task
def election_compute_tally(election_id):
    election = Election.objects.get(id=election_id)
    election.compute_tally()

    election_notify_admin.delay(election_id=election_id,
                                subject="encrypted tally computed",
                                body="""
The encrypted tally for election %s has been computed.

--
Helios
""" % election.name)

    if election.has_helios_trustee():
        tally_helios_decrypt.delay(election_id=election.id)


@shared_task
def tally_helios_decrypt(election_id):
    election = Election.objects.get(id=election_id)
    election.helios_trustee_decrypt()
    election_notify_admin.delay(election_id=election_id,
                                subject='Helios Decrypt',
                                body="""
Helios has decrypted its portion of the tally
for election %s.

--
Helios
""" % election.name)


@shared_task
def voter_file_process(voter_file_id):
    voter_file = VoterFile.objects.get(id=voter_file_id)
    voter_file.process()
    election_notify_admin.delay(election_id=voter_file.election.id,
                                subject='voter file processed',
                                body="""
Your voter file upload for election %s
has been processed.

%s voters have been created.

--
Helios
""" % (voter_file.election.name, voter_file.num_voters))


@shared_task
def notify_admin_opted_out_voters(election_id, opted_out_voters):
    election = Election.objects.get(id=election_id)
    
    if not opted_out_voters:
        return
    
    subject = f"Opted-out voters not added to election {election.name}"
    
    body = f"""
The following {len(opted_out_voters)} voters could not be added to election "{election.name}" 
because they have opted out of receiving Helios emails:

"""
    
    for voter in opted_out_voters:
        body += f"- {voter['name']} ({voter['email']}) [ID: {voter['voter_id']}, Type: {voter['voter_type']}]\n"
    
    optin_path = reverse('optin_form')
    optin_url = f"{settings.URL_HOST}{optin_path}"
    
    body += f"""

These voters will need to opt back in before they can be added to elections.
They can opt back in at: {optin_url}

--
Helios
"""
    
    election.admin.send_message(subject, body)


@shared_task
def election_notify_admin(election_id, subject, body):
    election = Election.objects.get(id=election_id)
    election.admin.send_message(subject, body)


@shared_task
def send_auto_reminders():
    """
    Check all elections and send auto-reminders to voters who haven't voted yet.
    This task should be run periodically (e.g., every hour via Celery Beat).
    """
    from helios import url_names
    
    logger = get_logger(send_auto_reminders.__name__)
    now = datetime.datetime.utcnow()
    
    # Find elections that:
    # 1. Have auto_reminder enabled
    # 2. Are currently in voting period (voting has started, not ended)
    # 3. Haven't sent a reminder yet
    # 4. Are close enough to the end time to send reminder
    
    elections = Election.objects.filter(
        auto_reminder_enabled_p=True,
        voting_started_at__isnull=False,  # voting has started
        voting_ends_at__isnull=False,     # has an end date
        voting_ended_at__isnull=True,     # voting has NOT ended yet
        auto_reminder_sent_at__isnull=True  # hasn't sent reminder yet
    )
    
    for election in elections:
        # Calculate the actual voting end time (check extension first, then scheduled end)
        voting_end = election.voting_extended_until or election.voting_ends_at
        
        if not voting_end:
            continue
            
        # Check if voting is still ongoing
        if now >= voting_end:
            continue
        
        # Calculate reminder time (hours before voting ends)
        reminder_hours = election.auto_reminder_hours or 24
        reminder_time = voting_end - datetime.timedelta(hours=reminder_hours)
        
        # Check if it's time to send the reminder
        if now >= reminder_time:
            logger.info(f"Sending auto-reminder for election {election.uuid} ({election.name})")
            
            # Send reminder to voters who haven't voted
            subject_template = 'email/vote_subject.txt'
            body_template = 'email/vote_body.txt'
            
            try:
                election_url = f"{settings.URL_HOST}{reverse(url_names.ELECTION_SHORTCUT, args=[election.short_name])}"
                election_vote_url = f"{settings.URL_HOST}{reverse(url_names.ELECTION_SHORTCUT_VOTE, args=[election.short_name])}"
            except Exception as e:
                logger.error(f"Failed to generate URLs for election {election.uuid}: {str(e)}")
                continue
            
            extra_vars = {
                'custom_subject': f"Reminder: Cast your vote in {election.name}",
                'custom_message': f"Voting ends soon! Please cast your vote before {voting_end.strftime('%Y-%m-%d %H:%M UTC')}.",
                'election_vote_url': election_vote_url,
                'election_url': election_url
            }
            
            # Queue email task for voters who haven't voted (vote_hash is None)
            voter_constraints_include = {'vote_hash': None}
            
            voters_email.delay(
                election_id=election.id,
                subject_template=subject_template,
                body_template=body_template,
                extra_vars=extra_vars,
                voter_constraints_include=voter_constraints_include
            )
            
            # Mark reminder as sent
            election.auto_reminder_sent_at = now
            election.save()
            
            logger.info(f"Auto-reminder queued for election {election.uuid}")
    
    logger.info(f"Auto-reminder check completed. Processed {len(elections)} elections.")
