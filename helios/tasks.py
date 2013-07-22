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

from zeus.core import from_canonical

@task()
def validate_mixing(election_id):
  election = Election.objects.get(id=election_id)
  election.zeus_election.validate_mixing()
  election_notify_admin.delay(election_id=election_id,
                                    subject="Mixing validated",
                                    body="Mixing validated")
  election.mixing_validated_at = datetime.datetime.now()
  election.save()
  election.store_encrypted_tally()
  tally_helios_decrypt.delay(election_id=election.id)


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

@task()
def tally_helios_decrypt(election_id):
    election = Election.objects.get(id = election_id)
    if not election.mixing_finished:
      raise Exception("Mixing not finished cannot decrypt")

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

    # no remote trustees
    if election.trustee_set.count() == 1 and election.has_helios_trustee():
        tally_decrypt.delay(election.pk)


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
    else:
        json_resp = json.dumps(ecount_response)
        election_notify_admin.delay(election_id, "Failed to post to ecounting", json_resp)
        e.ecounting_request_error = json_resp
        e.save()

@task()
def add_remote_mix(election_id, mix_tmp_file, mix_id=None):
    e = Election.objects.get(pk=election_id)
    tmp_file = file(mix_tmp_file)
    mix = from_canonical(tmp_file)
    error = e.add_remote_mix(mix, mix_id)
    if error:
        election_notify_admin.delay(election_id=election_id,
                                    subject="Remote mix failed to add",
                                    body=error)
        return

    election_notify_admin.delay(election_id=election_id,
                                subject="Remote mix added to election",
                                body=traceback.format_exc())
