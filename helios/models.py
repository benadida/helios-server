# -*- coding: utf-8 -*-
"""
Data Objects for Helios.

Ben Adida
(ben@adida.net)
"""

import traceback
import datetime
import logging
import uuid
import random
import StringIO
import copy
import base64
import zipfile
import os
import csv
import tempfile
import mmap
import marshal
import itertools
import urllib

from functools import wraps
from datetime import timedelta
from collections import defaultdict

from django.template.loader import render_to_string
from django.db import models, transaction
from django.db.models.query import QuerySet
from django.db.models import Count
from django.conf import settings
from django.core.mail import send_mail, mail_admins
from django.core.files import File
from django.utils.translation import ugettext_lazy as _
from django.core.validators import validate_email as django_validate_email
from django.forms import ValidationError
from django.core.urlresolvers import reverse
from django.core.context_processors import csrf
from django.utils import translation

from helios.crypto import electionalgs, algs, utils
from helios import utils as heliosutils
from helios import datatypes
from helios import exceptions
from helios.datatypes.djangofield import LDObjectField
from helios.byte_fields import ByteaField
from helios.utils import force_utf8


from heliosauth.models import User, AUTH_SYSTEMS
from heliosauth.jsonfield import JSONField
from helios.datatypes import LDObject

from zeus.core import (numbers_hash, mix_ciphers, gamma_encoding_max,
                       gamma_decode, to_absolute_answers, to_canonical)
from zeus.slugify import slughifi
from zeus.election_modules import ELECTION_MODULES_CHOICES, get_poll_module, \
    get_election_module

from zeus.model_features import ElectionFeatures, PollFeatures, \
        TrusteeFeatures, VoterFeatures
from zeus.model_tasks import TaskModel, PollTasks, ElectionTasks
from zeus import help_texts as help
from zeus.log import init_election_logger, init_poll_logger
from zeus.utils import decalize, get_filters, VOTER_SEARCH_FIELDS, \
    VOTER_BOOL_KEYS_MAP, VOTER_EXTRA_HEADERS, VOTER_TABLE_HEADERS


logger = logging.getLogger(__name__)

RESULTS_PATH = getattr(settings, 'ZEUS_RESULTS_PATH', os.path.join(settings.MEDIA_ROOT, 'results'))
ELECTION_MODEL_VERSION = 1


validate_email = lambda email,ln: django_validate_email(email)

class HeliosModel(TaskModel, datatypes.LDObjectContainer):

    class Meta:
        abstract = True


class PollMixQuerySet(QuerySet):

    def local(self):
        return self.filter(mix_type="local")

    def finished(self):
        return self.filter(status="finished")

    def mixing(self):
        return self.filter(status="mixing")

    def pending(self):
        return self.filter(status="pending")


class PollMixManager(models.Manager):

    def get_query_set(self):
        return PollMixQuerySet(self.model)

from django.core.files import storage
default_mixes_path = settings.MEDIA_ROOT + "/zeus_mixes/"
ZEUS_MIXES_PATH = getattr(settings, 'ZEUS_MIXES_PATH', default_mixes_path)
zeus_mixes_storage = storage.FileSystemStorage(location=ZEUS_MIXES_PATH)

class PollMix(models.Model):

    MIX_REMOTE_TYPE_CHOICES = (('helios', 'Helios'),
                                ('verificatum', 'Verificatum'),
                                ('zeus_client', 'Zeus server'))
    MIX_TYPE_CHOICES = (('local', 'Local'), ('remote', 'Remote'))
    MIX_STATUS_CHOICES = (('pending', 'Pending'), ('mixing', 'Mixing'),
                           ('validating', 'Validating'), ('error', 'Error'),
                           ('finished', 'Finished'))

    name = models.CharField(max_length=255, null=False, default='Zeus mixnet')
    mix_type = models.CharField(max_length=255, choices=MIX_TYPE_CHOICES,
                              default='local')
    poll = models.ForeignKey('Poll', related_name='mixes')
    mix_order = models.PositiveIntegerField(default=0)

    remote_ip = models.CharField(max_length=255, null=True, blank=True)
    remote_protocol = models.CharField(max_length=255,
                                     choices=MIX_REMOTE_TYPE_CHOICES,
                                     default='zeus_client')

    mixing_started_at = models.DateTimeField(null=True)
    mixing_finished_at = models.DateTimeField(null=True)

    status = models.CharField(max_length=255, choices=MIX_STATUS_CHOICES,
                            default='pending')
    mix_error = models.TextField(null=True, blank=True)
    mix_file = models.FileField(upload_to=lambda x:'',
                                storage=zeus_mixes_storage,
                                null=True, default=None)


    objects = PollMixManager()

    class Meta:
        ordering = ['-mix_order']
        unique_together = [('poll', 'mix_order')]


    def store_mix_in_file(self, mix):
        """
        Expects mix dict object
        """
        fname = str(self.pk) + ".canonical"
        fpath =  os.path.join(ZEUS_MIXES_PATH, fname)
        with open(fpath, "w") as f:
            to_canonical(mix, out=f)
        self.mix_file = fname
        self.save()

    def reset_mixing(self):
        if self.status == 'finished' and self.mix:
            raise Exception("Cannot reset finished mix")
        # TODO: also reset mix with higher that current mix_order
        self.mixing_started_at = None
        self.mix = None
        self.second_mix = None
        self.status = 'pending'
        self.mix_error = None
        self.save()
        self.parts.all().delete()
        return True

    def zeus_mix(self):
        filled_mix = ""
        for part in self.parts.order_by("pk"):
            filled_mix += part.data
        return marshal.loads(filled_mix)

    def get_original_ciphers(self):
        if self.mix_order == 0:
          return self.election.zeus.extract_votes_for_mixing()
        else:
          prev_mix = PollMix.objects.get(election=election,
                                         mix_order__lt=self.mix_order)
          return prev_mix.mixed_answers.get().zeus_mix()

    def mix_parts_iter(self, mix):
        size = len(mix)
        index = 0
        while index < size:
            yield buffer(mix, index, settings.MIX_PART_SIZE)
            index += settings.MIX_PART_SIZE

    def store_mix(self, mix):
        """
        mix is a dict object
        """
        self.parts.all().delete()
        mix = marshal.dumps(mix)

        for part in self.mix_parts_iter(mix):
            self.parts.create(data=part)

    @transaction.commit_on_success
    def _do_mix(self):
        zeus_mix = self.poll.zeus.get_last_mix()
        new_mix = self.poll.zeus.mix(zeus_mix)

        self.store_mix(new_mix)
        self.store_mix_in_file(new_mix)

        self.status = 'finished'
        self.save()
        return new_mix


    def mix_ciphers(self):
        if self.mix_type == "remote":
            raise Exception("Remote mixes not implemented yet.")

        self.mixing_started_at = datetime.datetime.now()
        self.status = 'mixing'
        self.save()

        try:
            self._do_mix()
        except Exception, e:
            self.status = 'error'
            self.mix_error = traceback.format_exc()
            self.parts.all().delete()
            self.save()
            raise


class MixPart(models.Model):
    mix = models.ForeignKey(PollMix, related_name="parts")
    data = ByteaField()


class ElectionManager(models.Manager):

    def get_queryset(self):
        return self.filter(deleted=False)

    def administered_by(self, user):
        if user.superadmin_p:
            return self.filter()

        return self.filter(admins__in=[user])


_default_voting_starts_at = lambda: datetime.datetime.now()
_default_voting_ends_at = lambda: datetime.datetime.now() + timedelta(hours=12)


class Election(ElectionTasks, HeliosModel, ElectionFeatures):

    OFFICIAL_CHOICES = (
        (None, _('Unresolved')),
        (0, _('Unofficial')),
        (1, _('Official')),
    )
    linked_polls = models.BooleanField(_('Linked polls'), default=False)
    election_module = models.CharField(_("Election type"), max_length=250,
                                         null=False,
                                         choices=ELECTION_MODULES_CHOICES,
                                         default='simple',
                                         help_text=help.election_module)
    version = models.CharField(max_length=255, default=ELECTION_MODEL_VERSION)
    uuid = models.CharField(max_length=50, null=False)
    name = models.CharField(_("Election name"), max_length=255,
                            help_text=help.election_name)
    short_name = models.CharField(max_length=255)
    communication_language = models.CharField("", max_length=5, null=True)
    help_email = models.CharField(_("Support email"),
                                  max_length=254, null=True, blank=True,
                                  help_text=help.help_email)
    help_phone = models.CharField(_("Support phone"),
                                  max_length=254, null=True, blank=True,
                                  help_text=help.help_phone)

    description = models.TextField(_("Election description"),
                                   help_text=help.election_description)
    trial = models.BooleanField(_("Trial election"), default=False,
                                help_text=help.trial)

    public_key = LDObjectField(type_hint = 'legacy/EGPublicKey', null=True)
    private_key = LDObjectField(type_hint = 'legacy/EGSecretKey', null=True)

    admins = models.ManyToManyField(User, related_name="elections")
    institution = models.ForeignKey('zeus.Institution', null=True)

    departments = models.TextField(_("Departments"), null=True,
                                   help_text=_("University Schools. e.g."
                                   "<br/><br/> School of Engineering <br />"
                                   "School of Medicine<br />School of"
                                   "Informatics<br />"))

    mix_key = models.CharField(max_length=50, default=None, null=True)
    remote_mixing_finished_at = models.DateTimeField(default=None, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    canceled_at = models.DateTimeField(default=None, null=True)
    cancelation_reason = models.TextField(default="")
    completed_at = models.DateTimeField(default=None, null=True)

    deleted = models.BooleanField(default=False)

    frozen_at = models.DateTimeField(default=None, null=True)
    voting_starts_at = models.DateTimeField(_("Voting starts at"),
                                            auto_now_add=False,
                                            default=_default_voting_starts_at,
                                            null=True,
                                            help_text=help.voting_starts_at)
    voting_ends_at = models.DateTimeField(_("Voting ends at"),
                                          auto_now_add=False,
                                          default=_default_voting_ends_at,
                                          null=True,
                                          help_text=help.voting_ends_at)
    voting_extended_until = models.DateTimeField(_("Voting extended until"),
                                                 auto_now_add=False,
                                                 default=None, blank=True,
                                                 null=True,
                                                 help_text=help.voting_extended_until)
    voting_ended_at = models.DateTimeField(auto_now_add=False, default=None,
                                           null=True)
    archived_at = models.DateTimeField(auto_now_add=False, default=None,
                                        null=True)
    official = models.IntegerField(null=True, default=None,
                                    choices=OFFICIAL_CHOICES)
    objects = ElectionManager()

    class Meta:
        ordering = ('-created_at', )

    def __init__(self, *args, **kwargs):
        self._logger = None
        super(Election, self).__init__(*args, **kwargs)

    @property
    def polls_by_link_id(self):
        linked = self.polls.exclude(link_id="").distinct("link_id")
        unlinked = self.polls.filter(link_id="")
        return itertools.chain(linked, unlinked)

    @property
    def voting_end_date(self):
        return self.voting_extended_until or self.voting_ends_at

    @property
    def zeus_stage(self):
        if not self.pk or not self.frozen_at:
            return 'CREATING'

        if not self.voting_ended_at:
            return 'VOTING'

        if not self.tallying_finished_at:
            return 'MIXING'

        if not self.mix_finished_at:
            return 'DECRYPTING'

        return 'FINISHED'

    def reset_logger(self):
        self._logger = None

    @property
    def logger(self):
        if not self._logger:
            self._logger = init_election_logger(self)
        return self._logger

    @property
    def zeus(self):
        from zeus import election
        obj = election.ZeusDjangoElection.from_election(self)
        obj.do_set_stage(self.zeus_stage)
        return obj

    @property
    def polls_issues_before_freeze(self):
        issues = {}
        for poll in self.polls.all():
            poll_issues = poll.issues_before_freeze
            if len(poll_issues) > 0:
                issues[poll] = poll_issues
        return issues

    @property
    def election_issues_before_freeze(self):
        issues = []
        trustees = Trustee.objects.filter(election=self)
        if len(trustees) == 0:
            issues.append({
                'type': 'trustees',
                'action': _("Add at least one trustee")
            })

        for t in trustees:
            if t.public_key == None:
                issues.append({
                    'type': 'trustee-keypairs',
                    'action': _('Have trustee %s generate a keypair') % t.name
                })

            if t.public_key and t.last_verified_key_at == None:
                issues.append({
                    'type': 'trustee-verification',
                    'action': _('Have trustee %s verify his key') % t.name
                })
        return issues

    def status_display_cls(self):
        if self.feature_canceled:
            return 'error alert'
        return ''

    def status_display(self):

      if self.feature_canceled:
          return _('Canceled')

      if self.feature_completed:
          return _('Completed')

      if self.feature_voting:
          return _('Voting')

      if self.polls_feature_compute_results_finished:
          return _('Results computed')

      if self.any_poll_feature_compute_results_running:
          return _('Computing results')

      if self.polls_feature_decrypt_finished:
          return _('Decryption finished')

      if self.any_poll_feature_decrypt_running:
          return _('Decrypting')

      if self.polls_feature_partial_decrypt_finished:
          return _('Partial decryptions finished')

      if self.any_poll_feature_can_partial_decrypt and \
          self.polls_feature_validate_mixing_finished:
          return _('Pending completion of partial decryptions')

      if self.any_poll_feature_validate_mixing_running or \
          self.any_poll_feature_validate_mixing_finished:
          return _('Validating mixing')

      if self.polls_feature_mix_finished:
          return _('Mixing finished')

      if self.any_poll_feature_mix_running or self.any_poll_feature_mix_finished:
          return _('Mixing')

      if self.any_poll_feature_validate_voting_running or \
          self.any_poll_feature_validate_voting_finished:
          return _('Validating voting')

      if self.feature_closed:
          return _('Election closed')

      if self.feature_frozen and not self.feature_voting_started:
          return _('Waiting for voting to start.')

      if self.feature_frozen and not self.feature_within_voting_date:
          return _('Voting stopped. Pending close.')

      if self.any_poll_feature_validate_create_running:
          return _('Freezing')

      if self.feature_frozen:
          return _('Frozen')

      return _('Election pending to freeze')

    def close_voting(self):
        self.voting_ended_at = datetime.datetime.now()
        self.save()
        self.logger.info("Voting closed")
        subject = "Election closed"
        msg = "Election closed"
        self.notify_admins(msg=msg, subject=subject)

    def freeze(self):
        for poll in self.polls.all():
            poll.freeze()

    def get_absolute_url(self):
        return "%s%s" % (settings.SECURE_URL_HOST,
                         reverse('election_index', args=(self.uuid,)))

    @property
    def cast_votes(self):
        return CastVote.objects.filter(poll__election=self)

    @property
    def voters(self):
        return Voter.objects.filter(poll__election=self)

    @property
    def audits(self):
        return AuditedBallot.objects.filter(poll__election=self)

    @property
    def casts(self):
        return CastVote.objects.filter(poll__election=self)

    def questions_count(self):
        count = 0
        for poll in self.polls.filter().only('questions_data'):
            count += len(poll.questions_data)
        return count

    def generate_mix_key(self):
        if self.mix_key:
            return self.mix_key
        else:
            self.mix_key = heliosutils.random_string(20)
        return self.mix_key

    def generate_trustee(self):
        """
        Generate the Zeus trustee.
        """

        if self.get_zeus_trustee():
            return self.get_zeus_trustee()

        self.zeus.create_zeus_key()
        return self.get_zeus_trustee()

    def get_zeus_trustee(self):
        trustees_with_sk = self.trustees.filter().zeus()
        if len(trustees_with_sk) > 0:
            return trustees_with_sk[0]
        else:
            return None

    def has_helios_trustee(self):
        return self.get_zeus_trustee() != None

    @transaction.commit_on_success
    def update_trustees(self, trustees):
        for name, email in trustees:
            trustee, created = self.trustees.get_or_create(email=email)
            if created:
                self.logger.info("Trustee %r created", trustee.email)
            # LOG TRUSTEE CREATED
            trustee.name = name
            trustee.save()

        if self.trustees.count() != len(trustees):
            emails = map(lambda t:t[1], trustees)
            for trustee in self.trustees.filter().no_secret():
                if not trustee.email in emails:
                    self.zeus.invalidate_election_public()
                    trustee.delete()
                    self.logger.info("Trustee %r deleted", trustee.email)
                    self.zeus.compute_election_public()
                    self.logger.info("Public key updated")
        self.auto_notify_trustees()

    def auto_notify_trustees(self, force=False):
        for trustee in self.trustees.exclude(secret_key__isnull=False):
            if not trustee.last_notified_at or force:
                trustee.send_url_via_mail()
    
    _zeus = None

    @property
    def zeus_stage(self):
        if not self.pk or not self.feature_frozen:
            return 'CREATING'

        if not self.voting_ended_at:
            return 'VOTING'

        if not self.mixing_finished:
            return 'MIXING'

        if self.mix_key and not self.remote_mixing_finished_at:
            return 'MIXING'

        if not self.results_compute_finished:
            return 'DECRYPTING'

        return 'FINISHED'

    def reprove_trustee(self, trustee):
        # public_key = trustee.public_key
        # pok = trustee.pok
        # self.zeus.reprove_trustee(public_key.y, [pok.commitment,
        #                                                  pok.challenge,
        #                                                  pok.response])
        self.logger.info("Trustee %r PK reproved", trustee.email)

        trustee.last_verified_key_at = datetime.datetime.now()
        trustee.save()

    def add_trustee_pk(self, trustee, public_key, pok):
        trustee.public_key = public_key
        trustee.pok = pok
        trustee.public_key_hash = utils.hash_b64(
            utils.to_json(
                trustee.public_key.toJSONDict()))
        trustee.last_verified_key_at = None
        trustee.save()
        # verify the pok
        trustee.send_url_via_mail()
        self.zeus.add_trustee(trustee.public_key.y, [pok.commitment,
                                                         pok.challenge,
                                                         pok.response])
        self.logger.info("Trustee %r PK updated", trustee.email)

    def notify_admins(self, msg='', subject='', send_anyway=False):
        """
        Notify admins with email
        """
        if send_anyway or (not self.trial):
            election_type = self.get_module().module_id
            trustees = self.trustees.all()
            admins = self.admins.all()
            context = {
                'election': self,
                'msg': msg,
                'election_type': election_type,
                'trustees': trustees,
                'admins': admins,
                'subject': subject,
            }

            body = render_to_string("email/admin_mail.txt", context)
            subject = render_to_string("email/admin_mail_subject.txt", context)
            mail_admins(subject.replace("\n", ""), body)

    def save(self, *args, **kwargs):
        if not self.uuid:
            self.uuid = unicode(uuid.uuid4())
        if not self.short_name:
            self.short_name = slughifi(self.name)
            es = Election.objects.filter()
            count = 1
            while es.filter(short_name=self.short_name).count() > 0:
                self.short_name = slughifi(self.name) + '-%d' % count
                count += 1

        super(Election, self).save(*args, **kwargs)

    def get_module(self):
        return get_election_module(self)


class PollQuerySet(QuerySet):
    pass


class PollManager(models.Manager):

    def get_query_set(self):
        return PollQuerySet(self.model).defer('encrypted_tally')



class Poll(PollTasks, HeliosModel, PollFeatures):

  link_id = models.CharField(_('Poll link group'), max_length=255, 
                             default='')
  linked_ref = models.CharField(_('Poll reference id'), max_length=255, 
                                default='')
  name = models.CharField(_('Poll name'), max_length=255)
  short_name = models.CharField(max_length=255)

  election = models.ForeignKey('Election', related_name="polls")

  uuid = models.CharField(max_length=50, null=False, unique=True, db_index=True)
  zeus_fingerprint = models.TextField(null=True, default=None)

  # dates at which this was touched
  frozen_at = models.DateTimeField(default=None, null=True)
  created_at = models.DateTimeField(auto_now_add=True)
  modified_at = models.DateTimeField(auto_now_add=True)

  questions = LDObjectField(type_hint = 'legacy/Questions',
                            null=True)
  questions_data = JSONField(null=True)

  # used only for homomorphic tallies
  encrypted_tally = LDObjectField(type_hint='phoebus/Tally',
                                  null=True)

  # results of the election
  result = LDObjectField(type_hint = 'phoebus/Result',
                         null=True)
  stv_results = JSONField(null=True)

  eligibles_count = models.PositiveIntegerField(default=5)
  has_department_limit = models.BooleanField(default=0)
  department_limit = models.PositiveIntegerField(default=0)

  voters_last_notified_at = models.DateTimeField(null=True, default=None)
  index = models.PositiveIntegerField(default=1)

  # voters oauth2 authentication
  oauth2_thirdparty = models.BooleanField(default=False)

  oauth2_type = models.CharField(max_length=25,
                                 null=True, blank=True)
  oauth2_client_type = models.CharField(max_length=25,
                                        null=True, blank=True)
  oauth2_client_id = models.CharField(max_length=255,
                                      null=True, blank=True)
  oauth2_client_secret = models.CharField(max_length=255,
                                          null=True, blank=True)
  oauth2_code_url = models.CharField(max_length=255,
                                null=True, blank=True)
  oauth2_exchange_url = models.CharField(max_length=255,
                                null=True, blank=True)
  oauth2_confirmation_url = models.CharField(max_length=255,
                                null=True, blank=True)
  oauth2_extra = models.CharField(max_length=255,
                                  null=True, blank=True)
  # jwt authentication
  jwt_auth = models.BooleanField(default=False)
  jwt_public_key = models.TextField(null=True, default=None)
  jwt_issuer = models.CharField(max_length=255,
                                null=True, blank=True)

  # shibboleth authentication
  shibboleth_auth = models.BooleanField(default=False)
  shibboleth_constraints = JSONField(default=None, null=True, blank=True)

  objects = PollManager()

  class Meta:
      ordering = ('link_id', 'index', 'created_at', )
      unique_together = (('name', 'election'),)

  def __init__(self, *args, **kwargs):
      self._logger = None
      super(Poll, self).__init__(*args, **kwargs)

  def get_shibboleth_constraints(self):
    defaults = {
        'assert_idp_key': 'MAIL',
        'assert_voter_key': 'email',
        'required_fields': ['REMOTE_USER', 'EPPN'],
        'endpoint': 'login'
    }
    default_constraints = getattr(settings, 'SHIBBOLETH_DEFAULT_CONSTRAINTS',
                                  defaults)
    constraints = {}
    constraints.update(default_constraints)
    constraints.update(self.shibboleth_constraints or {})
    return constraints

  @property
  def remote_login(self):
      return self.oauth2_thirdparty or self.jwt_auth

  @property
  def remote_login_display(self):
      if self.jwt_auth:
          return _("JSON Web Token Login")
      if self.oauth2_thirdparty:
          return _("Oauth2 Login %s") % self.oauth2_client_id
      return None

  def reset_logger(self):
      self._logger = None

  @property
  def has_linked_polls(self):
    if self.election.linked_polls and self.link_id.strip():
        return self.election.polls.filter(link_id=self.link_id).count() > 1
    return False

  @property
  def linked_polls(self):
    if self.election.linked_polls and self.link_id.strip():
        return self.election.polls.filter(link_id=self.link_id)
    return self.election.polls.filter(id=self.pk)
    
  def next_linked_poll(self, voter_id=None):
      linked_next = self.linked_polls.filter(index__gte=self.index)
      if voter_id:
          linked_next = linked_next.filter(voters__voter_login_id=voter_id)
      if linked_next.count() > 1:
          return linked_next[1]
      return None

  @property
  def logger(self):
      if not self._logger:
          self._logger = init_poll_logger(self)
      return self._logger

  @property
  def issues_before_freeze(self):
    issues = []
    if not self.questions:
        issues.append({
            "type": "questions",
            "action": _("Prepare poll questions")
        })
    if self.voters.count() == 0:
      issues.append({
          "type" : "voters",
          "action" : _('Import voters list')
          })

    return issues

  @property
  def zeus_stage(self):
    if not self.pk or not self.frozen_at:
        return 'CREATING'

    if not self.election.voting_ended_at:
        return 'VOTING'

    if not self.feature_mix_finished:
        return 'MIXING'

    if not self.result:
        return 'DECRYPTING'

    return 'FINISHED'

  _zeus = None

  @property
  def zeus(self):
      """
      Retrieve zeus core django
      """
      from zeus import election
      obj = election.ZeusDjangoElection.from_poll(self)
      obj.do_set_stage(self.zeus_stage)
      return obj

  @property
  def get_oauth2_module(self):
    from zeus import oauth2
    return oauth2.get_oauth2_module(self)
      

  def get_booth_url(self, request):
    vote_url = "%s/%s/booth/vote.html?%s" % (
            settings.SECURE_URL_HOST,
            settings.SERVER_PREFIX,
            urllib.urlencode({
                'token': csrf(request)['csrf_token'],
                'poll_url': "%s%s" % (settings.SECURE_URL_HOST,
                                      self.get_absolute_url()),
                'poll_json_url': "%s%s" % (settings.SECURE_URL_HOST,
                                           self.get_json_url()),
                'messages_url': "%s%s" % (settings.SECURE_URL_HOST,
                                          self.get_js_messages_url()),
                'language': "%s" % (request.LANGUAGE_CODE)
            }))
    return "%s?%s" % (reverse('test_cookie'),
                      urllib.urlencode({'continue_url': vote_url}))

  def get_absolute_url(self):
      return reverse('election_poll_index', args=[self.election.uuid,
                                                  self.uuid])

  def get_js_messages_url(self):
      return reverse('js_messages')

  def get_json_url(self):
      return reverse('election_poll_json', args=[self.election.uuid,
                                                  self.uuid])

  def get_module(self):
    return get_poll_module(self)

  def status_display(self):

      if self.election.feature_canceled:
          return _('Canceled')

      if self.election.feature_completed:
          return _('Completed')

      if self.feature_compute_results_finished:
          return _('Results computed')

      if self.feature_compute_results_running:
          return _('Computing results')

      if self.feature_decrypt_finished:
          return _('Decryption finished')

      if self.feature_decrypt_running:
          return _('Decrypting')

      if self.feature_partial_decrypt_running:
          return _('Waiting for all partial decryptions to finish')

      if self.feature_partial_decrypt_finished:
          return _('Partial decryptions finished')

      if self.election.feature_closed:
          return _('Voting closed')

      if self.election.feature_voting:
          return _('Voting')

      if self.election.feature_frozen:
          if self.election.feature_voting_date_passed:
              return _('Pending election close')

          return _('Freezed')

      if not self.questions_data:
          return _('No questions set')

      if not self.feature_voters_set:
          return _('No voters set')

      if not self.election.feature_frozen:
          return _('Ready to freeze')

  def name_display(self):
      return "%s, %s" % (self.election.name, self.name)

  def shortname_display(self):
      return "%s-%s" % (self.election.short_name, self.short_name)

  def get_last_mix(self):
    return self.mixnets.filter(status="finished").defer("data").order_by("-mix_order")[0]

  def get_booth_dict(self):
      cast_url = reverse('election_poll_cast',
                         args=[self.election.uuid, self.uuid])
      module = self.get_module()
      election = self.election

      public_key = {
        'g': str(election.public_key.g),
        'p': str(election.public_key.p),
        'q': str(election.public_key.q),
        'y': str(election.public_key.y),
      }

      data = {
          'cast_url': cast_url,
          'description': election.description,
          'frozen_at': self.frozen_at,
          'help_email': election.help_email,
          'help_phone': election.help_phone,
          'name': self.name,
          'election_name': election.name,
          'public_key': public_key,
          'questions': self.questions,
          'questions_data': self.questions_data,
          'election_module': module.module_id,
          'module_params': module.params,
          'uuid': self.uuid,
          'election_uuid': election.uuid,
          'voting_ends_at': election.voting_ends_at,
          'voting_starts_at': election.voting_starts_at,
          'voting_extended_until': election.voting_extended_until,
      }
      return data

  @property
  def cast_votes_count(self):
    return self.voters.exclude(vote=None).count()

  @property
  def audit_votes_cast_count(self):
    return self.audited_ballots.filter(is_request=False).count()

  @property
  def questions_count(self):
    if not self.questions_data:
      return 0
    else:
      return len(self.questions_data)

  @property
  def voters_count(self):
    return self.voters.count()

  @property
  def trustees_count(self):
    return self.trustees.filter(secret_key__isnull=True).count()

  @property
  def last_alias_num(self):
    """
    FIXME: we should be tracking alias number, not the V* alias which then
    makes things a lot harder
    """

    # FIXME: https://docs.djangoproject.com/en/dev/topics/db/multi-db/#database-routers
    # use database routes api to find proper database for the Voter model.
    # This will still work if someone deploys helios using only the default
    # database.
    SUBSTR_FUNCNAME = "substring"
    if 'sqlite' in settings.DATABASES['default']['ENGINE']:
        SUBSTR_FUNCNAME = "substr"

    sql = "select max(cast(%s(alias, 2) as integer)) from %s where " \
          "poll_id = %s"
    sql = sql % (SUBSTR_FUNCNAME, Voter._meta.db_table, self.id or 0)
    return heliosutils.one_val_raw_sql(sql) or 0

  @property
  def trustees_string(self):
    helios_trustee = self.get_zeus_trustee()
    trustees = [(t.name, t.email) for t in self.trustee_set.all() if \
                t != helios_trustee]
    return "\n".join(["%s,%s" % (t[0], t[1]) for t in trustees])

  def _init_questions(self, answers_count):
    if not self.questions:
        question = {}
        question['answer_urls'] = [None for x in range(answers_count)]
        question['choice_type'] = 'stv'
        question['question'] = 'Questions choices'
        question['answers'] = []
        question['result_type'] = 'absolute'
        question['tally_type'] = 'stv'
        self.questions = [question]

  def update_answers(self):
      module = self.get_module()
      module.update_answers()

  @property
  def tallied(self):
    return self.mixing_finished

  @property
  def encrypted_tally_hash(self):
    return self.workflow.tally_hash(self)

  def add_voters_file(self, uploaded_file):
    """
    expects a django uploaded_file data structure, which has filename, content,
    size...
    """
    # now we're just storing the content
    # random_filename = str(uuid.uuid4())
    # new_voter_file.voter_file.save(random_filename, uploaded_file)

    new_voter_file = VoterFile(poll=self,
                               voter_file_content=\
                               base64.encodestring(uploaded_file.read()))
    new_voter_file.save()
    return new_voter_file

  def election_progress(self):
    PROGRESS_MESSAGES = {
      'created': _('Election initialized.'),
      'candidates_added': _('Election candidates added.'),
      'votres_added': _('Election voters added.'),
      'keys_generated': _('Trustees keys generated.'),
      'opened': _('Election opened.'),
      'voters_notified': _('Election voters notified'),
      'voters_not_voted_notified': _('Election voters which not voted notified'),
      'extended': _('Election extension needed.'),
      'closed': _('Election closed.'),
      'tallied': _('Election tallied.'),
      'combined_decryptions': _('Trustees should decrypt results.'),
      'results_decrypted': _('Election results where decrypted.'),
    }

    OPTIONAL_STEPS = ['voters_not_voted_notified', 'extended']


  def voters_to_csv(self, q_param=None, to=None):
    if not to:
      to = StringIO.StringIO()

    writer = csv.writer(to)

    voters = self.voters.all()
    if q_param:
        voters = voters.filter(get_filters(q_param,VOTER_TABLE_HEADERS,
                                           VOTER_SEARCH_FIELDS,
                                           VOTER_BOOL_KEYS_MAP,
                                           VOTER_EXTRA_HEADERS))
    for voter in voters:
      vote_field = unicode(_("YES")) if voter.cast_votes.count() else \
                       unicode(_("NO"))
      if voter.excluded_at:
        vote_field += unicode(_("(EXCLUDED)"))

      writer.writerow(map(force_utf8, [voter.voter_login_id,
                                       voter.voter_email,
                                       voter.voter_name or '',
                                       voter.voter_surname or '',
                                       voter.voter_fathername or '',
                                       voter.voter_mobile or '',
                                       str(voter.voter_weight),
                                       vote_field
                                       ]))
    return to

  def last_voter_visit(self):
      try:
          return self.voters.filter(last_visit__isnull=False).order_by(
              '-last_visit')[0].last_visit
      except IndexError:
          return None

  def last_cast_date(self):
      try:
          last_cast = self.cast_votes.filter(
                    voter__excluded_at__isnull=True).order_by('-cast_at')[0]
      except IndexError:
          return ""

      return last_cast.cast_at

  def voters_visited_count(self):
      return self.voters.filter(last_visit__isnull=False).count()

  def voters_cast_count(self):
    return self.cast_votes.filter(
        voter__excluded_at__isnull=True).distinct('voter').count()

  def total_cast_count(self):
    return self.cast_votes.filter(
        voter__excluded_at__isnull=True).count()

  def mix_failed(self):
    try:
      return self.mixes.get(status="error")
    except PollMix.DoesNotExist:
      return None

  def mixes_count(self):
      return self.mixes.count()

  @property
  def finished_mixnets(self):
      return self.mixnets.filter(status='finished').defer('data')

  def mixing_errors(self):
      errors = []
      for e in self.mixnets.filter(mix_error__isnull=False,
                                   status='error').defer('data'):
          errors.append(e.mix_error)
      return errors

  def add_remote_mix(self, remote_mix, mix_name="Remote mix"):
    error = ''
    status = 'finished'
    mix_order = int(self.mixes_count())

    try:
        self.zeus.add_mix(remote_mix)
    except Exception, e:
        logging.exception("Remote mix failed")
        status = 'error'
        error = traceback.format_exc()

    try:
        with transaction.commit_on_success():
            mix = self.mixes.create(name=mix_name,
                                    mix_order=mix_order,
                                    mix_type='remote',
                                    mixing_started_at=datetime.datetime.now(),
                                    mixing_finished_at=datetime.datetime.now(),
                                    status=status,
                                    mix_error=error if error else None)
            mix.store_mix(remote_mix)
            mix.store_mix_in_file(remote_mix)
    except Exception, e:
        logging.exception("Remote mix creation failed.")
        return e

    with transaction.commit_on_success():
        if not Poll.objects.get(pk=self.pk).tallying_finished_at:
            mixnet.save()
        else:
            return "Mixing finished"

    return error

  @property
  def remote_mixes(self):
      return self.mixnets.filter(mix_type='remote',
                               status='finished').defer("data")

  def get_mix_url(self):
    if not self.mix_key:
      return ''
    return settings.URL_HOST + "/helios/elections/%s/mix/%s" % (self.uuid, self.mix_key)

  def mixes_count(self):
    mixnets_count = self.mixnets.filter(status="finished",
                        second_mix__isnull=False).count() * 2
    mixnets_count += self.mixnets.filter(status="finished",
                                         second_mix__isnull=True).count()
    return mixnets_count

  def _get_zeus_vote(self, enc_vote, voter=None, audit_password=None):
    answer = enc_vote.encrypted_answers[0]
    cipher = answer.choices[0]
    alpha, beta = cipher.alpha, cipher.beta
    modulus, generator, order = self.zeus.do_get_cryptosystem()
    commitment, challenge, response = enc_vote.encrypted_answers[0].encryption_proof
    fingerprint = numbers_hash((modulus, generator, alpha, beta,
                                commitment, challenge, response))

    zeus_vote = {
      'fingerprint': fingerprint,
      'encrypted_ballot': {
          'beta': beta,
          'alpha': alpha,
          'commitment': commitment,
          'challenge': challenge,
          'response': response,
          'modulus': modulus,
          'generator': generator,
          'order': order,
          'public': self.election.public_key.y
      }
    }

    if hasattr(answer, 'answer') and answer.answer:
      zeus_vote['audit_code'] = audit_password
      zeus_vote['voter_secret'] = answer.randomness[0]

    if audit_password:
      zeus_vote['audit_code'] = audit_password

    if voter:
      zeus_vote['voter'] = voter.uuid

    return zeus_vote

  def cast_vote(self, voter, enc_vote, audit_password=None):
    zeus_vote = self._get_zeus_vote(enc_vote, voter, audit_password)
    return self.zeus.cast_vote(zeus_vote)

  def zeus_proofs_path(self):
    return os.path.join(settings.ZEUS_PROOFS_PATH, '%s-%s.zip' %
                        (self.election.uuid, self.uuid))

  def store_zeus_proofs(self):
    if not self.result:
      return None

    zip_path = self.zeus_proofs_path()
    if os.path.exists(zip_path):
      os.unlink(zip_path)

    export_data = self.zeus.export()
    self.zeus_fingerprint = export_data[0]['election_fingerprint']
    self.save()

    zf = zipfile.ZipFile(zip_path, mode='w')
    data_info = zipfile.ZipInfo('%s_proofs.txt' % self.short_name)
    data_info.compress_type = zipfile.ZIP_DEFLATED
    data_info.comment = "Election %s (%s-%s) zeus proofs" % (self.zeus_fingerprint,
                                                          self.election.uuid, self.uuid)
    data_info.date_time = datetime.datetime.now().timetuple()
    data_info.external_attr = 0777 << 16L

    tmpf = tempfile.TemporaryFile(mode="w", suffix='.zeus',
                                  prefix='tmp', dir='/tmp')
    to_canonical(export_data[0], out=tmpf)
    tmpf.flush()
    size = tmpf.tell()
    zeus_data = mmap.mmap(tmpf.fileno(), 0, mmap.MAP_SHARED, mmap.PROT_READ)
    zf.writestr(data_info, zeus_data)
    zf.close()
    tmpf.close()

  @property
  def pretty_result(self):
    from helios.counter import Counter
    cands_count = len(self.questions[0]['answers'])
    answers = self.questions[0]['answers']
    candidates_selections = []
    decoded_selections = []
    abs_selections = []
    answer_selections = []
    selections = []

    for vote in self.result[0]:
        decoded = vote
        selection = gamma_decode(vote, cands_count, cands_count)
        abs_selection = to_absolute_answers(selection, cands_count)
        cands = [answers[i] for i in abs_selection]
        cands_objs = [self.candidates[i].update() for i in abs_selection]
        cands_objs = []
        for i in abs_selection:
          obj = self.candidates[i]
          obj['selection_index'] = i + 1
          cands_objs.append(obj)

        selections.append(selection)
        abs_selections.append(abs_selection)
        answer_selections.append(cands)
        candidates_selections.append(cands_objs)
    decoded_selections.append(decoded)

    return {'selections': selections, 'abs_selections': abs_selections,
            'answer_selections': answer_selections,
            'candidates_selections': candidates_selections,
            'decoded_selections': decoded}

  def get_result_file_path(self, name, ext):
    election = self.short_name
    return os.path.join(settings.MEDIA_ROOT, 'results', '%s-%s-results.%s' % \
                        (election, name ,ext))

  def generate_result_docs(self):
    import json
    results_json = self.zeus.get_results()

    # json file
    jsonfile = file(self.get_result_file_path('json', 'json'), 'w')
    json.dump(results_json, jsonfile)
    jsonfile.close()

    # pdf report
    if self.get_module().module_id =='score':
        from zeus.results_report import build_doc
        build_doc(_(u'Results'), self.election.name,
                  self.election.institution.name,
                  self.election.voting_starts_at, self.election.voting_ends_at,
                  self.election.voting_extended_until,
                  [(self.name, json.dumps(results_json), 
                    self.questions_data, 
                    self.questions[0]['answers'])],
                  self.get_result_file_path('pdf', 'pdf'), score=True)

        from zeus.reports import csv_from_score_polls
        csvfile = file(self.get_result_file_path('csv', 'csv'), "w")
        csv_from_score_polls(self.election, [self], csvfile)
        csvfile.close()
    else:
        from zeus.results_report import build_doc
        results_name = self.election.name
        parties = self.get_module().module_id == 'parties'
        build_doc(_(u'Results'), self.election.name,
                  self.election.institution.name,
                  self.election.voting_starts_at, self.election.voting_ends_at,
                  self.election.voting_extended_until,
                  [(self.name, json.dumps(results_json), 
                    self.questions_data, 
                    self.questions[0]['answers'])],
                  self.get_result_file_path('pdf', 'pdf'), parties=parties)

        # CSV
        from zeus.reports import csv_from_polls
        csvfile = file(self.get_result_file_path('csv', 'csv'), "w")
        csv_from_polls(self.election, [self], csvfile)
        csvfile.close()


  def save(self, *args, **kwargs):
    if not self.uuid:
      self.uuid = str(uuid.uuid4())
    if not self.short_name:
      self.short_name = slughifi(self.name)
      es = self.election.polls.filter()
      count = 1
      while es.filter(short_name=self.short_name).count() > 0:
        self.short_name = slughifi(self.name) + '-%d' % count
        count += 1
    super(Poll, self).save(*args, **kwargs)



class ElectionLog(models.Model):
  """
  a log of events for an election
  """

  FROZEN = "frozen"
  VOTER_FILE_ADDED = "voter file added"
  DECRYPTIONS_COMBINED = "decryptions combined"

  election = models.ForeignKey(Election)
  log = models.CharField(max_length=500)
  at = models.DateTimeField(auto_now_add=True)

##
## Craziness for CSV
##

def csv_reader(csv_data, min_fields=2, max_fields=6, **kwargs):
    if not isinstance(csv_data, str):
        m = "Please provide string data to csv_reader, not %s" % type(csv_data)
        raise ValueError(m)
    encodings = ['utf-8', 'iso8859-7', 'utf-16', 'utf-16le', 'utf-16be']
    encodings.reverse()
    rows = []
    append = rows.append
    while 1:
        if not encodings:
            m = "Cannot decode csv data!"
            raise ValueError(m)
        encoding = encodings[-1]
        try:
            data = csv_data.decode(encoding)
            data = data.strip(u'\ufeff')
            if data.count(u'\x00') > 0:
                m = "Wrong encoding detected (heuristic)"
                raise ValueError(m)
            if data.count(u'\u2000') > data.count(u'\u0020'):
                m = "Wrong endianess (heuristic)"
                raise ValueError(m)
            break
        except (UnicodeDecodeError, ValueError), e:
            encodings.pop()
            continue

    for i, line in enumerate(data.splitlines()):
        line = line.strip()
        if not line:
            continue
        cells = line.split(',', max_fields)
        if len(cells) < min_fields:
            cells = line.split(';')
            if len(cells) < min_fields:
                m = ("line %d: CSV must have at least %d fields "
                     "(email, last_name, name)" % (i+1, min_fields))
                raise ValueError(m)
        cells += [u''] * (max_fields - len(cells))
        append(cells)

    return rows

def iter_voter_data(voter_data, email_validator=validate_email):
    reader = csv_reader(voter_data, min_fields=2, max_fields=7)

    line = 0
    for voter_fields in reader:
        line += 1
        # bad line
        if len(voter_fields) < 1:
            continue

        return_dict = {}

        # strip leading/trailing whitespace from all fields
        for i, f in enumerate(voter_fields):
            voter_fields[i] = f.strip()

        if len(voter_fields) < 2:
            m = _("There must be at least two fields, Registration ID and Email")
            raise ValidationError(m)

        return_dict['voter_id'] = voter_fields[0]
        email = voter_fields[1]
        email_validator(email, line)
        return_dict['email'] = email
        if len(voter_fields) == 2:
            yield return_dict
            continue

        name = voter_fields[2]
        return_dict['name'] = name
        if len(voter_fields) == 3:
            yield return_dict
            continue

        surname = voter_fields[3]
        return_dict['surname'] = surname
        if len(voter_fields) == 4:
            yield return_dict
            continue

        fathername = voter_fields[4]
        return_dict['fathername'] = fathername
        if len(voter_fields) == 5:
            yield return_dict
            continue

        mobile = voter_fields[5]
        if mobile:
            mobile = mobile.replace(' ', '')
            mobile = mobile.replace('-', '')
            if len(mobile) < 4 or not mobile[1:].isdigit or \
                (mobile[0] != '+' and not mobile[0].isdigit()):
                    m = _("Malformed mobile phone number: %s") % mobile
                    raise ValidationError(m)
        return_dict['mobile'] = mobile

        weight = voter_fields[6]
        if weight:
            try:
                weight = int(weight)
                if weight <= 0:
                    raise ValueError()
            except ValueError:
                m = _("Voter weight must be a positive integer, not %s")
                m = m % weight
                raise ValidationError(m)
            return_dict['weight'] = weight

        yield return_dict

        if len(voter_fields) > 7:
            m = _("Invalid voter data at line %s") %line
            raise ValidationError(m)


class VoterFile(models.Model):
  """
  A model to store files that are lists of voters to be processed.
  Format:
     registration_id, email, name, surname, extra_name, mobile_number.
  Note:
     - All fields are strings, stripped from leading/trailing whitespace.
     - There will be one vote per registration_id
     - Multiple registration_ids can have the same email
       (more than one votes per person)
     - Multiple emails per registration_id will update this voters email.

  """
  # path where we store voter upload
  PATH = settings.VOTER_UPLOAD_REL_PATH

  poll = models.ForeignKey(Poll)

  # we move to storing the content in the DB
  voter_file = models.FileField(upload_to=PATH, max_length=250,null=True)
  voter_file_content = models.TextField(null=True)

  uploaded_at = models.DateTimeField(auto_now_add=True)
  processing_started_at = models.DateTimeField(auto_now_add=False, null=True)
  processing_finished_at = models.DateTimeField(auto_now_add=False, null=True)
  num_voters = models.IntegerField(null=True)

  def itervoters(self, email_validator=validate_email):
    if self.voter_file_content:
      voter_data = base64.decodestring(self.voter_file_content)
    else:
      voter_data = open(self.voter_file.path, "r").read()

    return iter_voter_data(voter_data, email_validator=email_validator)

  @transaction.commit_on_success
  def process(self, linked=True, check_dupes=True):
    demo_voters = 0
    poll = self.poll
    demo_user = False
    for user in poll.election.admins.all():
        if user.user_id.startswith('demo_'):
            demo_user = True

    nr = sum(e.voters.count() for e in user.elections.all())
    demo_voters += nr
    if demo_voters >= settings.DEMO_MAX_VOTERS and demo_user:
        raise exceptions.VoterLimitReached("No more voters for demo account")

    self.processing_started_at = datetime.datetime.utcnow()
    self.save()

    # now we're looking straight at the content
    if self.voter_file_content:
      voter_data = base64.decodestring(self.voter_file_content)
    else:
      voter_data = open(self.voter_file.path, "r").read()

    reader = iter_voter_data(voter_data)

    last_alias_num = poll.last_alias_num

    num_voters = 0
    new_voters = []
    for voter in reader:
      num_voters += 1
      voter_id = voter['voter_id']
      email = voter['email']
      name = voter.get('name', '')
      surname = voter.get('surname', '')
      fathername = voter.get('fathername', '')
      mobile = voter.get('mobile', '')
      weight = voter.get('weight', 1)

      voter = None
      try:
          if check_dupes:
            voter = Voter.objects.get(poll=poll, voter_login_id=voter_id)
            m = _("Duplicate voter id"
                    " : %s"%voter_id)
            raise exceptions.DuplicateVoterID(m)
      except Voter.DoesNotExist:
          pass
      # create the voter
      if not voter:
        demo_voters += 1
        if demo_voters > settings.DEMO_MAX_VOTERS and demo_user:
          raise exceptions.VoterLimitReached("No more voters for demo account")

      linked_polls = poll.linked_polls
      if not linked:
          linked_polls = linked_polls.filter(pk=poll.pk)

      for poll in linked_polls:
        new_voters = []
        voter = None
        try:
            voter = Voter.objects.get(poll=poll, voter_login_id=voter_id)
        except Voter.DoesNotExist:
            pass
        if not voter:
            voter_uuid = str(uuid.uuid4())
            voter = Voter(uuid=voter_uuid, voter_login_id=voter_id,
                        voter_name=name, voter_email=email, poll=poll,
                        voter_surname=surname, voter_fathername=fathername,
                        voter_mobile=mobile, voter_weight=weight)
            voter.init_audit_passwords()
            voter.generate_password()
            new_voters.append(voter)
            voter.save()
        else:
            voter.voter_name = name
            voter.voter_surname = surname
            voter.voter_fathername = fathername
            voter.voter_email = email
            voter.voter_mobile = mobile
            voter.voter_weight = weight
            voter.save()

        voter_alias_integers = range(last_alias_num+1, last_alias_num+1+num_voters)
        random.shuffle(voter_alias_integers)
        for i, voter in enumerate(new_voters):
            voter.alias = 'V%s' % voter_alias_integers[i]
            voter.save()

    self.num_voters = num_voters
    self.processing_finished_at = datetime.datetime.utcnow()
    self.save()

    return num_voters


class VoterQuerySet(QuerySet):

    def not_excluded(self):
        return self.filter(excluded_at__isnull=True)

    def excluded(self):
        return self.filter(excluded_at__isnull=False)

    def cast(self):
        return self.filter().not_excluded().annotate(
            num_cast=Count('cast_votes')).filter(num_cast__gte=1)

    def nocast(self):
        return self.filter().not_excluded().annotate(
            num_cast=Count('cast_votes')).filter(num_cast=0)

    def invited(self):
        return self.filter(last_booth_invitation_send_at__isnull=False)

    def visited(self):
        return self.filter(last_visit__isnull=False)

class VoterManager(models.Manager):

    def get_query_set(self):
        return VoterQuerySet(self.model)


class Voter(HeliosModel, VoterFeatures):
  poll = models.ForeignKey(Poll, related_name="voters")
  uuid = models.CharField(max_length = 50)


  # if user is null, then you need a voter login ID and password
  voter_login_id = models.CharField(max_length = 100, null=True)
  voter_password = models.CharField(max_length = 100, null=True)
  voter_name = models.CharField(max_length = 200, null=True)
  voter_surname = models.CharField(max_length = 200, null=True)
  voter_email = models.CharField(max_length = 250, null=True)
  voter_fathername = models.CharField(max_length = 250, null=True)
  voter_mobile = models.CharField(max_length = 48, null=True)
  voter_weight = models.PositiveIntegerField(default=1)

  # if election uses aliases
  alias = models.CharField(max_length = 100, null=True)

  # we keep a copy here for easy tallying
  vote = LDObjectField(type_hint = 'phoebus/EncryptedVote',
                       null=True)
  vote_hash = models.CharField(max_length = 100, null=True)
  vote_fingerprint = models.CharField(max_length=255)
  vote_signature = models.TextField()
  vote_index = models.PositiveIntegerField(null=True)

  cast_at = models.DateTimeField(auto_now_add=False, null=True)
  audit_passwords = models.CharField(max_length=200, null=True)

  last_sms_send_at = models.DateTimeField(null=True)
  last_sms_code = models.CharField(max_length=100, blank=True, null=True)
  last_email_send_at = models.DateTimeField(null=True)
  last_booth_invitation_send_at = models.DateTimeField(null=True)
  last_visit = models.DateTimeField(null=True)

  excluded_at = models.DateTimeField(null=True, default=None)
  exclude_reason = models.TextField(default='')

  objects = VoterManager()

  class Meta:
    unique_together = (('poll', 'voter_login_id'), ('poll', 'voter_password'))

  user = None

  @property
  def linked_voters(self):
      return Voter.objects.filter(poll__in=self.poll.linked_polls,
                                  voter_login_id=self.voter_login_id)

  def get_cast_votes(self):
      return self.cast_votes.filter()

  def __init__(self, *args, **kwargs):
    super(Voter, self).__init__(*args, **kwargs)

    # stub the user so code is not full of IF statements
    if not self.user:
      self.user = User(user_type='password', user_id=self.voter_email,
                       name=u"%s %s" % (self.voter_name, self.voter_surname))

  @property
  def login_code(self):
      return "%d-%s" % (self.poll.pk, decalize(str(self.voter_password)))

  @property
  def voted(self):
      return self.cast_votes.count() > 0

  @property
  def zeus_string(self):
    return u"%s %s %s %s <%s>" % (self.voter_name, self.voter_surname,
                                  self.voter_fathername or '',
                                  self.voter_mobile or '', self.voter_login_id)
  @property
  def full_name(self):
    return u"%s %s %s (%s)" % (self.voter_name, self.voter_surname,
                               self.voter_fathername or '', self.voter_email)

  def init_audit_passwords(self):
    if not self.audit_passwords:
      passwords = ""
      for i in range(4):
        passwords += heliosutils.random_string(5) + "|"

      self.audit_passwords = passwords

  def get_audit_passwords(self):
    if not self.audit_passwords or not self.audit_passwords.strip():
      return []

    return filter(bool, self.audit_passwords.split("|"))

  def get_quick_login_url(self):
      url = reverse('election_poll_voter_booth_login', kwargs={
          'election_uuid': self.poll.election.uuid,
          'poll_uuid': self.poll.uuid,
          'voter_uuid': self.uuid,
          'voter_secret': self.voter_password
      });
      return settings.URL_HOST + url

  def check_audit_password(self, password):
    if password != "" and password not in self.get_audit_passwords():
      return True

    return False

  @classmethod
  @transaction.commit_on_success
  def register_user_in_election(cls, user, election):
    voter_uuid = str(uuid.uuid4())
    voter = Voter(uuid= voter_uuid, user = user, election = election)

    # do we need to generate an alias?
    heliosutils.lock_row(Election, election.id)
    alias_num = election.last_alias_num + 1
    voter.alias = "V%s" % alias_num

    voter.save()
    return voter

  @classmethod
  def get_by_election(cls, election, cast=None, order_by='voter_login_id', after=None, limit=None):
    """
    FIXME: review this for non-GAE?
    """
    query = cls.objects.filter(election = election)

    # the boolean check is not stupid, this is ternary logic
    # none means don't care if it's cast or not
    if cast == True:
      query = query.exclude(cast_at = None)
    elif cast == False:
      query = query.filter(cast_at = None)

    # little trick to get around GAE limitation
    # order by uuid only when no inequality has been added
    if cast == None or order_by == 'cast_at' or order_by =='-cast_at':
      query = query.order_by(order_by)

      # if we want the list after a certain UUID, add the inequality here
      if after:
        if order_by[0] == '-':
          field_name = "%s__gt" % order_by[1:]
        else:
          field_name = "%s__gt" % order_by
        conditions = {field_name : after}
        query = query.filter (**conditions)

    if limit:
      query = query[:limit]

    return query

  @classmethod
  def get_all_by_election_in_chunks(cls, election, cast=None, chunk=100):
    return cls.get_by_election(election)

  @classmethod
  def get_by_election_and_voter_id(cls, election, voter_id):
    try:
      return cls.objects.get(poll= election, voter_email = voter_id)
    except cls.DoesNotExist:
      return None

  @classmethod
  def get_by_election_and_user(cls, election, user):
    try:
      return cls.objects.get(election = election, user = user)
    except cls.DoesNotExist:
      return None

  @classmethod
  def get_by_election_and_uuid(cls, election, uuid):
    query = cls.objects.filter(election = election, uuid = uuid)

    try:
      return query[0]
    except:
      return None

  @classmethod
  def get_by_user(cls, user):
    return cls.objects.select_related().filter(user = user).order_by('-cast_at')

  @property
  def datatype(self):
    return self.election.datatype.replace('Election', 'Voter')

  @property
  def vote_tinyhash(self):
    """
    get the tinyhash of the latest castvote
    """
    if not self.vote_hash:
      return None

    return CastVote.objects.get(vote_hash = self.vote_hash).vote_tinyhash

  @property
  def election_uuid(self):
    return self.election.uuid

  @property
  def name(self):
    return self.voter_name

  @property
  def voter_id(self):
    return self.user.user_id

  @property
  def voter_id_hash(self):
    if self.voter_login_id:
      # for backwards compatibility with v3.0, and since it doesn't matter
      # too much if we hash the email or the unique login ID here.
      value_to_hash = self.voter_login_id
    else:
      value_to_hash = self.voter_id

    try:
      return utils.hash_b64(value_to_hash)
    except:
      try:
        return utils.hash_b64(value_to_hash.encode('latin-1'))
      except:
        return utils.hash_b64(value_to_hash.encode('utf-8'))

  @property
  def voter_type(self):
    return self.user.user_type

  @property
  def display_html_big(self):
    return self.user.display_html_big

  def send_message(self, subject, body):
    self.user.send_message(subject, body)

  def generate_password(self, length=10):
    if not self.voter_password:
      self.voter_password = heliosutils.random_string(12)
      existing = Voter.objects.filter(
          poll=self.poll).exclude(pk=self.pk)
      while existing.filter(voter_password=self.voter_password).count() > 1:
        self.voter_password = heliosutils.random_string(12)

  def store_vote(self, cast_vote):
    # only store the vote if it's cast later than the current one
    if self.cast_at and cast_vote.cast_at < self.cast_at:
      return

    self.vote = cast_vote.vote
    self.vote_hash = cast_vote.vote_hash
    self.cast_at = cast_vote.cast_at
    self.save()

  def last_cast_vote(self):
    return CastVote(vote = self.vote, vote_hash = self.vote_hash, cast_at = self.cast_at, voter=self)


class CastVoteQuerySet(QuerySet):

    def distinct_voter(self):
        return self.distinct('voter')

    def countable(self):
        return self.filter(voter__excluded_at__isnull=True)

    def excluded(self):
        return self.filter(voter__excluded_at__isnull=False)


class CastVoteManager(models.Manager):

    def get_query_set(self):
        return CastVoteQuerySet(self.model)


class CastVote(HeliosModel):
  # the reference to the voter provides the voter_uuid
  voter = models.ForeignKey(Voter, related_name="cast_votes")
  poll = models.ForeignKey(Poll, related_name="cast_votes")

  previous = models.CharField(max_length=255, default="")

  # the actual encrypted vote
  vote = LDObjectField(type_hint='phoebus/EncryptedVote')

  # cache the hash of the vote
  vote_hash = models.CharField(max_length=100)

  # a tiny version of the hash to enable short URLs
  vote_tinyhash = models.CharField(max_length=50, null=True, unique=True)

  cast_at = models.DateTimeField(auto_now_add=True)
  audit_code = models.CharField(max_length=100, null=True)

  # some ballots can be quarantined (this is not the same thing as provisional)
  quarantined_p = models.BooleanField(default=False, null=False)
  released_from_quarantine_at = models.DateTimeField(auto_now_add=False,
                                                     null=True)

  # when is the vote verified?
  verified_at = models.DateTimeField(null=True)
  invalidated_at = models.DateTimeField(null=True)
  fingerprint = models.CharField(max_length=255)
  signature = JSONField(null=True)
  index = models.PositiveIntegerField(null=True)

  objects = CastVoteManager()

  class Meta:
    unique_together = (('poll', 'index'),)
    ordering = ('-cast_at',)

  @property
  def datatype(self):
    return self.voter.datatype.replace('Voter', 'CastVote')

  @property
  def voter_uuid(self):
    return self.voter.uuid

  @property
  def voter_hash(self):
    return self.voter.hash

  @property
  def is_quarantined(self):
    return self.quarantined_p and not self.released_from_quarantine_at

  def set_tinyhash(self):
    """
    find a tiny version of the hash for a URL slug.
    """
    safe_hash = self.vote_hash
    for c in ['/', '+']:
      safe_hash = safe_hash.replace(c,'')

    length = 8
    while True:
      vote_tinyhash = safe_hash[:length]
      if CastVote.objects.filter(vote_tinyhash = vote_tinyhash).count() == 0:
        break
      length += 1

    self.vote_tinyhash = vote_tinyhash

  def save(self, *args, **kwargs):
    """
    override this just to get a hook
    """
    # not saved yet? then we generate a tiny hash
    if not self.vote_tinyhash:
      self.set_tinyhash()

    super(CastVote, self).save(*args, **kwargs)


class AuditedBallotQuerySet(QuerySet):

    def confirmed(self):
        return self.filter(is_request=False)

    def requests(self):
        return self.filter(is_request=True)


class AuditedBallotManager(models.Manager):

    def get_query_set(self):
        return AuditedBallotQuerySet(self.model)


class AuditedBallot(models.Model):
  """
  ballots for auditing
  """
  poll = models.ForeignKey(Poll, related_name="audited_ballots")
  voter = models.ForeignKey(Voter, null=True)
  raw_vote = models.TextField()
  vote_hash = models.CharField(max_length=100)
  added_at = models.DateTimeField(auto_now_add=True)
  fingerprint = models.CharField(max_length=255)
  audit_code = models.CharField(max_length=100)
  is_request = models.BooleanField(default=True)
  signature = JSONField(null=True)

  objects = AuditedBallotManager()

  @property
  def choices(self):
    answers = self.poll.questions[0]['answers']
    nr_answers = len(answers)
    encoded = self.vote.encrypted_answers[0].answer
    max_encoded = gamma_encoding_max(nr_answers)
    if encoded > max_encoded:
        choices = []
    else:
        selection = gamma_decode(encoded, nr_answers)
        choices = to_absolute_answers(selection, nr_answers)
    return map(lambda x:answers[x], choices)

  @classmethod
  def get(cls, election, vote_hash):
    return cls.objects.get(election = election, vote_hash = vote_hash,
                           is_request=False)

  @classmethod
  def get_by_election(cls, election, after=None, limit=None, extra={}):
    query = cls.objects.filter(election =
                               election).order_by('-pk').filter(**extra)

    # if we want the list after a certain UUID, add the inequality here
    if after:
      query = query.filter(vote_hash__gt = after)

    query = query.filter(is_request=False)
    if limit:
      query = query[:limit]

    return query

  @property
  def vote(self):
    return electionalgs.EncryptedVote.fromJSONDict(
                utils.from_json(self.raw_vote))
  class Meta:
    unique_together = (('poll', 'is_request', 'fingerprint'))


class TrusteeDecryptionFactorsQuerySet(QuerySet):

    def no_secret(self):
        return self.filter(trustee__secret_key__isnull=True)

    def completed(self):
        return self.filter(decryption_factors__isnull=False).filter(
            decryption_proofs__isnull=False)


class TrusteeDecryptionFactorsManager(models.Manager):

    def get_query_set(self):
        return TrusteeDecryptionFactorsQuerySet(self.model)


class TrusteeDecryptionFactors(models.Model):

  trustee = models.ForeignKey('Trustee', related_name='partial_decryptions')
  poll = models.ForeignKey('Poll', related_name='partial_decryptions')
  decryption_factors = LDObjectField(
      type_hint=datatypes.arrayOf(datatypes.arrayOf('core/BigInteger')),
      null=True)
  decryption_proofs = LDObjectField(
      type_hint=datatypes.arrayOf(datatypes.arrayOf('legacy/EGZKProof')),
      null=True)

  objects = TrusteeDecryptionFactorsManager()

  class Meta:
      unique_together = (('trustee', 'poll'),)


class TrusteeQuerySet(QuerySet):

    def no_secret(self):
        return self.filter(secret_key__isnull=True)

    def zeus(self):
        return self.filter(secret_key__isnull=False)


class TrusteeManager(models.Manager):

    def get_query_set(self):
        return TrusteeQuerySet(self.model)


class Trustee(HeliosModel, TrusteeFeatures):
    election = models.ForeignKey(Election, related_name="trustees")
    uuid = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    secret = models.CharField(max_length=100)
    public_key = LDObjectField(type_hint = 'legacy/EGPublicKey', null=True)
    public_key_hash = models.CharField(max_length=100)
    secret_key = LDObjectField(type_hint = 'legacy/EGSecretKey', null=True)
    pok = LDObjectField(type_hint = 'legacy/DLogProof', null=True)
    last_verified_key_at = models.DateTimeField(null=True)
    last_notified_at = models.DateTimeField(null=True, default=None)

    objects = TrusteeManager()

    @property
    def get_partial_decryptions(self):
        for poll in self.election.polls.all():
            try:
                pd = poll.partial_decryptions.filter().only(
                    'poll').get(trustee=self)
                yield (poll, pd.decryption_factors)
            except TrusteeDecryptionFactors.DoesNotExist:
                yield (poll, None)

    def generate_password(self):
        if not self.secret:
            self.secret = heliosutils.random_string(12)
            existing = Trustee.objects.filter(
                election=self.election).exclude(pk=self.pk)
            while existing.filter(secret=self.secret).count() > 1:
                self.secret = heliosutils.random_string(12)

    def save(self, *args, **kwargs):
        if not self.uuid:
            self.uuid = str(uuid.uuid4())
        # set secret password
        self.generate_password()
        super(Trustee, self).save(*args, **kwargs)

    def get_login_url(self):
        url = settings.SECURE_URL_HOST + reverse('election_trustee_login',
                                                 args=[self.election.uuid,
                                                 self.email, self.secret])
        return url

    def pending_partial_decryptions(self):
        return filter(lambda p: p[1], self.get_partial_decryptions())

    def get_step(self):
        """
        Step based on trustee/election state
        """
        if not self.public_key:
            return 1
        if not self.last_verified_key_at:
            return 2
        if self.pending_partial_decryptions:
            return 3
        return 1

    STEP_TEXTS = [_(u'Create trustee key'),
                  _(u'Verify trustee key'),
                  _(u'Partially decrypt votes')]

    def send_url_via_mail(self, msg=''):
        """
        Notify trustee
        """
        lang = self.election.communication_language
        with translation.override(lang):
            url = self.get_login_url()
            context = {
                'election_name': self.election.name,
                'election': self.election,
                'url': url,
                'msg': msg,
                'step': self.get_step(),
                'step_text': self.STEP_TEXTS[self.get_step()-1]
            }

            body = render_to_string("trustee_email.txt", context)
            subject = render_to_string("trustee_email_subject.txt", context)

            send_mail(subject.replace("\n", ""),
                      body,
                      settings.SERVER_EMAIL,
                      ["%s <%s>" % (self.name, self.email)],
                      fail_silently=False)
            self.election.logger.info("Trustee %r login url send", self.email)
            self.last_notified_at = datetime.datetime.now()
            self.save()

    
    @property
    def datatype(self):
        return self.election.datatype.replace('Election', 'Trustee')
