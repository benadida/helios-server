"""
Celery queued tasks for Helios

2010-08-01
ben@adida.net
"""
import copy
from celery import shared_task
from celery.utils.log import get_logger

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

    # Filter out opted-out voters by checking their email hashes
    opted_out_hashes = set(EmailOptOut.objects.values_list('email_hash', flat=True))
    
    filtered_voters = []
    for voter in voters:
        voter_email = voter.voter_email or (voter.user and voter.user.user_id)
        if voter_email:
            email_hash = utils.hash_email(voter_email)
            if email_hash not in opted_out_hashes:
                filtered_voters.append(voter)
        else:
            # If no email, include in list (shouldn't happen in practice)
            filtered_voters.append(voter)
    
    logger = get_logger(voters_email.__name__)
    logger.info(f"Sending emails to {len(filtered_voters)} voters (filtered out {len(voters) - len(filtered_voters)} opted-out)")

    for voter in filtered_voters:
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
        the_vars.update({
            'unsubscribe_url': f"/optout/confirm/{voter_email}/{unsubscribe_code}/",
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
    """
    Notify election admin about voters who couldn't be added due to opt-out status.
    
    Args:
        election_id: ID of the election
        opted_out_voters: List of dicts with voter info (email, name, voter_id, voter_type)
    """
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
    
    body += f"""

These voters will need to opt back in before they can be added to elections.
They can opt back in at: /optin/

--
Helios
"""
    
    election.admin.send_message(subject, body)


@shared_task
def election_notify_admin(election_id, subject, body):
    election = Election.objects.get(id=election_id)
    election.admin.send_message(subject, body)
