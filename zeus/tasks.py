import traceback
import copy
import datetime
import json
import urllib, urllib2
import logging

from functools import wraps
from celery.decorators import task as celery_task

from helios.models import Election, Voter, Poll
from helios.view_utils import render_template_raw

from django.template import Context, Template, loader
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.utils import translation
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.db import transaction

from zeus.core import from_canonical
from zeus import mobile
from zeus import utils
from email.Utils import formataddr


logger = logging.getLogger(__name__)


def task(*taskargs, **taskkwargs):
    """
    Task helper to automatically initialize django mechanism using the
    default language set in project settings.
    """
    def wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            prev_language = translation.get_language()
            if prev_language != settings.LANGUAGE_CODE:
                translation.activate(settings.LANGUAGE_CODE)
            return func(*args, **kwargs)
        # prevent magic kwargs passthrough
        if not 'accept_magic_kwargs' in taskkwargs:
            taskkwargs['accept_magic_kwargs'] = False
        return celery_task(*taskargs, **taskkwargs)(inner)
    return wrapper


def poll_task(*taskargs, **taskkwargs):
    def wrapper(func):
        #if not 'rate_limit' in taskkwargs:
            #taskkwargs['rate_limit'] = '5/m'
        return task(*taskargs, **taskkwargs)(func)
    return wrapper


@task(rate_limit=getattr(settings, 'ZEUS_VOTER_EMAIL_RATE', '20/m'),
      ignore_result=True)
def single_voter_email(voter_uuid, subject_template, body_template,
                       extra_vars={}, update_date=True,
                       update_booth_invitation_date=False):
    voter = Voter.objects.get(uuid=voter_uuid)
    lang = voter.poll.election.communication_language
    with translation.override(lang):
        the_vars = copy.copy(extra_vars)
        the_vars.update({'voter' : voter, 'poll': voter.poll,
                         'election': voter.poll.election})
        subject = render_template_raw(None, subject_template, the_vars)
        body = render_template_raw(None, body_template, the_vars)
        linked_voters = voter.linked_voters
        if update_date:
            for voter in linked_voters:
                voter.last_email_send_at = datetime.datetime.now()
                voter.save()
        if update_booth_invitation_date:
            for voter in linked_voters:
                voter.last_booth_invitation_send_at = datetime.datetime.now()
                voter.save()
        voter.user.send_message(subject, body)


@task(ignore_result=True)
def voters_email(poll_id, subject_template, body_template, extra_vars={},
                 voter_constraints_include=None,
                 voter_constraints_exclude=None,
                 update_date=True,
                 update_booth_invitation_date=False,
                 q_param=None):
    poll = Poll.objects.get(id=poll_id)
    voters = poll.voters.filter(utils.get_voters_filters_with_constraints(
        q_param, voter_constraints_include, voter_constraints_exclude
    ))

    if len(poll.linked_polls) > 1 and 'vote_body' in body_template:
        body_template = body_template.replace("_body.txt", "_linked_body.txt")

    for voter in voters:
        single_voter_email.delay(voter.uuid,
                                 subject_template,
                                 body_template,
                                 extra_vars,
                                 update_date,
                                 update_booth_invitation_date)


@task(rate_limit=getattr(settings, 'ZEUS_VOTER_EMAIL_RATE', '20/m'),
      ignore_result=True)
def send_cast_vote_email(poll_pk, voter_pk, signature):
    poll = Poll.objects.get(pk=poll_pk)
    election = poll.election
    lang = election.communication_language
    voter = poll.voters.filter().get(pk=voter_pk)

    with translation.override(lang):
        subject = _("%(election_name)s - vote cast") % {
          'election_name': election.name,
          'poll_name': poll.name
    }

        body = _(u"""You have successfully cast a vote in

%(election_name)s
%(poll_name)s
    
as

%(voter_name)s %(voter_surname)s
with registration ID: %(reg_id)s

you can find your encrypted vote attached in this mail.
""") % {
    'election_name': election.name,
    'poll_name': poll.name,
    'voter_name': voter.voter_name,
    'voter_surname': voter.voter_surname,
    'reg_id': voter.voter_login_id,
}
    # send it via the notification system associated with the auth system
    attachments = [('vote.signature', signature['signature'], 'text/plain')]
    name = "%s %s" % (voter.voter_name, voter.voter_surname)
    to = formataddr((name, voter.voter_email))
    message = EmailMessage(subject, body, settings.SERVER_EMAIL, [to])
    for attachment in attachments:
        message.attach(*attachment)

    message.send(fail_silently=False)


@poll_task(ignore_result=True)
def poll_validate_create(poll_id):
    poll = Poll.objects.select_for_update().get(id=poll_id)
    poll.validate_create()


@task(ignore_result=True)
def election_validate_create(election_id):
    election = Election.objects.select_for_update().get(id=election_id)
    election.logger.info("Spawning validate create poll tasks")
    if election.polls_feature_frozen:
        election.frozen_at = datetime.datetime.now()
        election.save()

    for poll in election.polls.all():
        if not poll.feature_can_validate_create:
            poll_validate_create.delay(poll.id)

    subject = u"Election is frozen"
    msg = u"Election is frozen"
    msg = utils.append_ballot_to_msg(election, msg)
    election.notify_admins(msg=msg, subject=subject)

@task(ignore_result=True)
def election_validate_voting(election_id):
    election = Election.objects.select_for_update().get(pk=election_id)
    election.logger.info("Spawning validate voting poll tasks")
    for poll in election.polls.all():
        if poll.feature_can_validate_voting:
            poll_validate_voting.delay(poll.pk)


@poll_task(ignore_result=True)
def poll_validate_voting(poll_id):
    poll = Poll.objects.select_for_update().get(pk=poll_id)
    poll.validate_voting()
    if poll.election.polls_feature_validate_voting_finished:
        subject = "Validate voting finished"
        msg = "Validate voting finished"
        poll.election.notify_admins(msg=msg, subject=subject)
        election_mix.delay(poll.election.pk)


@task(ignore_result=True)
def election_mix(election_id):
    election = Election.objects.select_for_update().get(pk=election_id)
    election.logger.info("Spawning mix poll tasks")
    for poll in election.polls.all():
        if poll.feature_can_mix:
            poll_mix.delay(poll.pk)


@poll_task(ignore_result=True)
def poll_mix(poll_id):
    poll = Poll.objects.select_for_update().get(pk=poll_id)
    poll.mix()
    if poll.election.polls_feature_mix_finished:
        subject = "Mixing finished"
        msg = "Mixing finished"
        poll.election.notify_admins(msg=msg, subject=subject)
        election_validate_mixing.delay(poll.election.pk)


@task(ignore_result=True)
def election_validate_mixing(election_id):
    election = Election.objects.select_for_update().get(pk=election_id)
    election.logger.info("Spawning validate mix poll tasks")
    for poll in election.polls.all():
        if poll.feature_can_validate_mixing:
            poll_validate_mixing.delay(poll.pk)


@poll_task(ignore_result=True)
def poll_validate_mixing(poll_id):
    poll = Poll.objects.select_for_update().get(pk=poll_id)
    poll.validate_mixing()
    if poll.election.polls_feature_validate_mixing_finished:
        subject = "Validate mixing finished"
        msg = "Validate mixing finished"
        poll.election.notify_admins(msg=msg, subject=subject)
        election_zeus_partial_decrypt.delay(poll.election.pk)


@task(ignore_result=True)
def notify_trustees(election_id):
    election = Election.objects.get(pk=election_id)
    for trustee in election.trustees.filter().no_secret():
        trustee.send_url_via_mail()


@task(ignore_result=True)
def election_zeus_partial_decrypt(election_id):
    election = Election.objects.select_for_update().get(pk=election_id)
    election.logger.info("Spawning zeus partial decrypt poll tasks")
    notify_trustees.delay(election.pk)
    for poll in election.polls.all():
        if poll.feature_can_zeus_partial_decrypt:
            poll_zeus_partial_decrypt.delay(poll.pk)


@poll_task(ignore_result=True)
def poll_zeus_partial_decrypt(poll_id):
    poll = Poll.objects.select_for_update().get(pk=poll_id)
    poll.zeus_partial_decrypt()
    if poll.election.trustees.filter().no_secret().count() == 0:
        poll.partial_decrypt_started_at = datetime.datetime.now()
        poll.partial_decrypt_finished_at = datetime.datetime.now()
        poll.save()
    if poll.election.polls_feature_partial_decryptions_finished:
        election_decrypt.delay(poll.election.pk)


@poll_task(ignore_result=True)
def poll_add_trustee_factors(poll_id, trustee_id, factors, proofs):
    poll = Poll.objects.select_for_update().get(pk=poll_id)
    trustee = poll.election.trustees.get(pk=trustee_id)
    poll.partial_decrypt(trustee, factors, proofs)
    if poll.election.polls_feature_partial_decryptions_finished:
        election_decrypt.delay(poll.election.pk)


@task(ignore_result=True)
def election_decrypt(election_id):
    election = Election.objects.select_for_update().get(pk=election_id)
    election.logger.info("Spawning decrypt poll tasks")
    subject = "Trustees partial decryptions finished"
    msg = "Trustees partial decryptions finished"
    election.notify_admins(msg=msg, subject=subject)
    for poll in election.polls.all():
        if poll.feature_can_decrypt:
            poll_decrypt.delay(poll.pk)


@poll_task(ignore_result=True)
def poll_decrypt(poll_id):
    poll = Poll.objects.select_for_update().get(pk=poll_id)
    poll.decrypt()
    if poll.election.polls_feature_decrypt_finished:
        subject = "Decryption finished"
        msg = "Decryption finished"
        poll.election.notify_admins(msg=msg, subject=subject)
        election_compute_results.delay(poll.election.pk)


@task(ignore_result=True)
def election_compute_results(election_id):
    election = Election.objects.select_for_update().get(pk=election_id)
    election.logger.info("Spawning compute results poll tasks")
    for poll in election.polls.all():
        if poll.feature_can_compute_results:
            poll_compute_results.delay(poll.pk)


@poll_task(ignore_result=True)
def poll_compute_results(poll_id):
    poll = Poll.objects.select_for_update().get(pk=poll_id)
    poll.compute_results()
    if poll.election.polls_feature_compute_results_finished:
        e = poll.election
        e.completed_at = datetime.datetime.now()
        e.save()
        e.compute_results()
        subject = "Results computed - docs generated"
        msg = "Results computed - docs generated"
        e.notify_admins(msg=msg, subject=subject)



@task(ignore_result=False)
def send_voter_sms(voter_id, tpl, override_mobile=None, resend=False,
                   dry=True):
    voter = Voter.objects.select_related().get(pk=voter_id)
    if not voter.voter_mobile and not override_mobile:
        raise Exception("Voter mobile field not set")

    dlr_url = settings.SECURE_URL_HOST + reverse('election_poll_sms_delivery', args=(voter.poll.election.uuid, voter.poll.uuid))
    client = mobile.get_client(voter.poll.election.uuid, dlr_url=dlr_url)
    message = ""
    context = Context({
        'voter': voter,
        'poll': voter.poll,
        'election': voter.poll.election,
        'reg_code': voter.voter_login_id,
        'login_code': voter.login_code,
        'email': voter.voter_email,
        'secret': voter.voter_password,
        'SECURE_URL_HOST': settings.SECURE_URL_HOST
    })
    t = Template(tpl)
    message = t.render(context)

    # identify and sanitize mobile number
    voter_mobile = override_mobile or voter.voter_mobile
    try:
        voter_mobile = utils.sanitize_mobile_number(voter_mobile)
    except Exception, e:
        return False, "Invalid number (%s)" % str(voter_mobile)

    # do not resend if asked to
    if not resend and voter.last_sms_send_at:
        print "Skipping. Message already sent at %r" % voter.last_sms_send_at

    if dry:
        # dry/testing mode
        print 10 * "-"
        print "TO: ", voter_mobile
        print "FROM: ", client.from_mobile
        print "MESSAGE (%d) :" % len(message)
        print message
        print 10 * "-"
        sent, error_or_code = True, "FAKE_ID"
    else:
        # call to the API
        poll = voter.poll
        poll.logger.info("Sending SMS to %s, (%s - %s)", voter_mobile,
                         voter.voter_login_id, voter.voter_mobile)
        sent, error_or_code = client.send(voter_mobile, message)
        msg_uid = client._last_uid
        if not sent:
            poll.logger.error("Failed to send %r (%r, %r)", msg_uid, sent,
                              error_or_code)
        else:
            poll.logger.info("SMS sent %r (%r, %r)", msg_uid, sent,
                             error_or_code)
        if sent:
            # store last notification date
            voter.last_sms_send_at = datetime.datetime.now()
            voter.last_sms_code = client.id + ":" + error_or_code
            if not client.remote_status:
                voter.last_sms_status = 'sent'
            voter.save()

    return sent, error_or_code


@task(ignore_result=False)
def check_sms_status(voter_id, code, election_uuid=None):
    voter = Voter.objects.select_related().get(pk=voter_id)
    if voter.last_sms_status:
        return voter.last_sms_status

    client = mobile.get_client(election_uuid)
    return client.status(code)
