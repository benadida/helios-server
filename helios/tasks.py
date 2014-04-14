"""
Celery queued tasks for Helios

2010-08-01
ben@adida.net
"""

from celery.decorators import task

from models import *
from view_utils import render_template_raw
import signals

import copy


@task()
def cast_vote_verify_and_store(cast_vote_id, status_update_message=None, **kwargs):
    cast_vote = CastVote.objects.get(id=cast_vote_id)
    result = cast_vote.verify_and_store()

    voter = cast_vote.voter
    election = voter.election
    user = voter.user

    if result:
        # send the signal
        signals.vote_cast.send(sender=election, election=election, user=user, voter=voter, cast_vote=cast_vote)

        if status_update_message and user.can_update_status():
            user.update_status(status_update_message)

    else:
        logger = cast_vote_verify_and_store.get_logger(**kwargs)
        logger.error("Failed to verify and store %d" % cast_vote_id)


@task()
def voters_email(election_id, subject_template, body_template, extra_vars={}, voter_constraints_include=None, voter_constraints_exclude=None):
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


@task()
def voters_notify(election_id, notification_template, extra_vars={}):
    election = Election.objects.get(id=election_id)
    for voter in election.voter_set.all():
        single_voter_notify.delay(voter.uuid, notification_template, extra_vars)


@task()
def single_voter_email(voter_uuid, subject_template, body_template, extra_vars={}):
    voter = Voter.objects.get(uuid=voter_uuid)
    the_vars = copy.copy(extra_vars)
    the_vars.update({'voter': voter})

    subject = render_template_raw(None, subject_template, the_vars)
    body = render_template_raw(None, body_template, the_vars)

    voter.send_message(subject, body)


@task()
def single_voter_notify(voter_uuid, notification_template, extra_vars={}):
    voter = Voter.objects.get(uuid=voter_uuid)

    the_vars = copy.copy(extra_vars)
    the_vars.update({'voter': voter})

    notification = render_template_raw(None, notification_template, the_vars)

    voter.user.send_notification(notification)


@task()
def election_compute_tally(election_id):
    election = Election.objects.get(id=election_id)
    election.compute_tally()

    body = """The encrypted tally for election %s has been computed.

--
Helios
""" % election.name

    admin_email.delay(election_id, "%s - Encrypted Tally Computed" % election.name, body)

    if election.has_helios_trustee():
        tally_helios_decrypt.delay(election_id=election.id)

    if election.use_threshold:
        trustees = Trustee.get_by_election(election)

        for trustee in trustees:
            if not trustee.helios_trustee:
                url = settings.SECURE_URL_HOST + reverse(trustee_login, args=[election.short_name, trustee.email, trustee.secret])

                # send a note to trustee
                body = """Dear %s,

The election administrator has computed the encrypted tally.
Before the result can be release, you will have to compute your partial encryption.

As a reminder, your trustee dashboard is at:

    %s

--
Helios""" % (trustee.name, url)

                single_trustee_email.delay(trustee.id, "%s - Compute Partial Decryption" % election.name, body)


@task()
def tally_helios_decrypt(election_id):
    election = Election.objects.get(id=election_id)
    election.helios_trustee_decrypt()

    body = """Helios has decrypted its portion of the tally for election %s.

--
Helios
""" % election.name

    admin_email.delay(election_id, "%s - Helios Decryption" % election.name, body)


@task()
def voter_file_process(voter_file_id):
    voter_file = VoterFile.objects.get(id=voter_file_id)
    voter_file.process()

    body = """Your uploaded voter file for election %s has been processed.
%s voters have been created.

--
Helios
""" % (voter_file.election.name, voter_file.num_voters)

    admin_email.delay(voter_file.election.id, "%s - Voter File Processed" % voter_file.election.name, body)


@task()
def admin_email(election_id, subject, body):
    election = Election.objects.get(id=election_id)
    election.admin.send_message(subject, body)


@task()
def single_trustee_email(trustee_id, subject, body):
    trustee = Trustee.objects.get(id=trustee_id)
    trustee.send_message(subject, body)


@task()
def add(x, y):
    return x + y


@task()
def change_name(election_id, name):
    election = Election.objects.get(id=election_id)
    election.name = name
    election.save()  # save object in database
    return election
