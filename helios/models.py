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
import json as json_module
import base64

import helios.views

from django.db import models, transaction
from django.utils import simplejson
from django.conf import settings
from django.core.mail import send_mail
from django.utils.translation import ugettext_lazy as _
from django.core.validators import validate_email
from django.forms import ValidationError

from helios.crypto import electionalgs, algs, utils
from helios import utils as heliosutils
from helios import datatypes
from helios.datatypes.djangofield import LDObjectField
from helios.workflows import get_workflow_module


# useful stuff in auth
from heliosauth.models import User, AUTH_SYSTEMS
from heliosauth.jsonfield import JSONField
from helios.datatypes import LDObject

from zeus.core import numbers_hash, mix_ciphers, gamma_decode, \
    to_absolute_answers

class HeliosModel(models.Model, datatypes.LDObjectContainer):
  class Meta:
    abstract = True

class ElectionMixnet(HeliosModel):

  MIXNET_REMOTE_TYPE_CHOICES = (('helios', 'Helios'),
                                ('verificatum', 'Verificatum'))
  MIXNET_TYPE_CHOICES = (('local', 'Local'), ('remote', 'Remote'))
  MIXNET_STATUS_CHOICES = (('pending', 'Pending'), ('mixing', 'Mixing'),
                           ('error', 'Error'), ('finished', 'Finished'))

  name = models.CharField(max_length=255, null=False, default='Helios mixnet')
  mixnet_type = models.CharField(max_length=255, choices=MIXNET_TYPE_CHOICES,
      default='local')
  election = models.ForeignKey('Election', related_name='mixnets')
  mix_order = models.PositiveIntegerField(default=0)

  remote_ip = models.CharField(max_length=255, null=True, blank=True)
  remote_protocol = models.CharField(max_length=255, choices=MIXNET_REMOTE_TYPE_CHOICES,
      default='helios')

  mixing_started_at = models.DateTimeField(null=True)
  mixing_finished_at = models.DateTimeField(null=True)
  status = models.CharField(max_length=255, choices=MIXNET_STATUS_CHOICES, default='pending')
  mix_error = models.TextField(null=True, blank=True)
  mix = JSONField(null=True)


  class Meta:
    ordering = ['-mix_order']
    unique_together = [('election', 'mix_order')]

  def can_mix(self):
    return self.status in ['pending'] and not self.election.tallied

  def reset_mixing(self):
    if self.status == 'finished' and self.mix:
      raise Exception("Cannot reset finished mixnet")

    # TODO: also reset mixnets with higher that current mix_order
    self.mixing_started_at = None
    self.mix = None
    self.status = 'pending'
    self.mix_error = None
    self.save()
    return True

  def zeus_mix(self):
    return self.mix

  def get_original_ciphers(self):
    if self.mix_order == 0:
      return self.election.zeus_election.extract_votes_for_mixing()
    else:
      prev_mixnet = Mixnet.objects.get(election=election, mix_order=self.mix_order-1)
      return prev_mixnet.mixed_answers.get().zeus_mix()

  @transaction.commit_on_success
  def _do_mix(self):
    zeus_mix = self.election.zeus_election.get_last_mix()
    new_mix = self.election.zeus_election.mix(zeus_mix)
    self.mix = new_mix
    self.status = 'finished'
    self.save()
    return new_mix

  def mix_ciphers(self):
    if not self.can_mix():
      raise Exception("Cannot initialize mixing. Already mixed ???")

    if self.mixnet_type == "remote":
      raise Exception("Remote mixnets not implemented yet.")

    self._do_mix()
    self.mixing_started_at = datetime.datetime.now()
    self.status = 'mixing'
    self.save()

    try:
        self._do_mix()
    except Exception, e:
        self.status = 'error'
        print traceback.format_exc()
        self.mix_error = traceback.format_exc()
        self.save()
        self.notify_admin_for_mixing_error()

  def notify_admin_for_mixing_error(self):
    pass

class Election(HeliosModel):
  admins = models.ManyToManyField(User, related_name="elections")
  institution = models.ForeignKey('zeus.Institution', null=True)
  eligibles_count = models.PositiveIntegerField(default=5)
  has_department_limit = models.BooleanField(default=1)
  help_email = models.CharField(max_length=254, null=True, blank=True)
  help_phone = models.CharField(max_length=254, null=True, blank=True)
  send_email_on_cast_done = models.BooleanField(default=True)

  uuid = models.CharField(max_length=50, null=False)

  # keep track of the type and version of election, which will help dispatch to the right
  # code, both for crypto and serialization
  # v3 and prior have a datatype of "legacy/Election"
  # v3.1 will still use legacy/Election
  # later versions, at some point will upgrade to "2011/01/Election"
  datatype = models.CharField(max_length=250, null=False, default="legacy/Election")

  short_name = models.CharField(max_length=100)
  name = models.CharField(max_length=110)

  candidates = JSONField(default="{}")
  departments = JSONField(default="[]")

  ELECTION_TYPES = (
    ('election', 'Election'),
    ('referendum', 'Referendum')
    )

  WORKFLOW_TYPES = (
    ('homomorphic', 'Homomorphic'),
    ('mixnet', 'Mixnet')
  )

  election_type = models.CharField(max_length=250, null=False, default='election', choices = ELECTION_TYPES)
  workflow_type = models.CharField(max_length=250, null=False, default='homomorphic',
      choices = WORKFLOW_TYPES)
  private_p = models.BooleanField(default=False, null=False)

  description = models.TextField()
  public_key = LDObjectField(type_hint = 'legacy/EGPublicKey',
                             null=True)
  private_key = LDObjectField(type_hint = 'legacy/EGSecretKey',
                              null=True)

  questions = LDObjectField(type_hint = 'legacy/Questions',
                            null=True)

  # eligibility is a JSON field, which lists auth_systems and eligibility details for that auth_system, e.g.
  # [{'auth_system': 'cas', 'constraint': [{'year': 'u12'}, {'year':'u13'}]}, {'auth_system' : 'password'}, {'auth_system' : 'openid', 'constraint': [{'host':'http://myopenid.com'}]}]
  eligibility = LDObjectField(type_hint = 'legacy/Eligibility',
                              null=True)

  # open registration?
  # this is now used to indicate the state of registration,
  # whether or not the election is frozen
  openreg = models.BooleanField(default=False)

  # featured election?
  featured_p = models.BooleanField(default=False)

  # voter aliases?
  use_voter_aliases = models.BooleanField(default=False)
  use_advanced_audit_features = models.BooleanField(default=True, null=False)

  # where votes should be cast
  cast_url = models.CharField(max_length = 500)

  # dates at which this was touched
  created_at = models.DateTimeField(auto_now_add=True)
  modified_at = models.DateTimeField(auto_now_add=True)

  # dates at which things happen for the election
  frozen_at = models.DateTimeField(auto_now_add=False, default=None, null=True)
  archived_at = models.DateTimeField(auto_now_add=False, default=None, null=True)

  # dates for the election steps, as scheduled
  # these are always UTC
  registration_starts_at = models.DateTimeField(auto_now_add=False, default=None, null=True)
  voting_starts_at = models.DateTimeField(auto_now_add=False, default=None, null=True)
  voting_ends_at = models.DateTimeField(auto_now_add=False, default=None, null=True)

  # if this is non-null, then a complaint period, where people can cast a quarantined ballot.
  # we do NOT call this a "provisional" ballot, since provisional implies that the voter has not
  # been qualified. We may eventually add this, but it can't be in the same CastVote table, which
  # is tied to a voter.
  complaint_period_ends_at = models.DateTimeField(auto_now_add=False, default=None, null=True)

  tallying_starts_at = models.DateTimeField(auto_now_add=False, default=None, null=True)

  # dates when things were forced to be performed
  voting_started_at = models.DateTimeField(auto_now_add=False, default=None, null=True)
  voting_extended_until = models.DateTimeField(auto_now_add=False, default=None, null=True)
  voting_ended_at = models.DateTimeField(auto_now_add=False, default=None, null=True)
  tallying_started_at = models.DateTimeField(auto_now_add=False, default=None, null=True)
  tallying_finished_at = models.DateTimeField(auto_now_add=False, default=None, null=True)
  tallies_combined_at = models.DateTimeField(auto_now_add=False, default=None, null=True)

  # the hash of all voters (stored for large numbers)
  voters_hash = models.CharField(max_length=100, null=True)

  # encrypted tally, each a JSON string
  # used only for homomorphic tallies
  encrypted_tally = LDObjectField(type_hint='phoebus/Tally',
                                  null=True)

  # results of the election
  result = LDObjectField(type_hint = 'phoebus/Result',
                         null=True)

  # decryption proof, a JSON object
  # no longer needed since it's all trustees
  result_proof = JSONField(null=True)

  @property
  def pretty_type(self):
    return dict(self.ELECTION_TYPES)[self.election_type]

  @property
  def num_cast_votes(self):
    return self.voter_set.exclude(vote=None).count()

  @property
  def num_voters(self):
    return self.voter_set.count()

  @property
  def num_trustees(self):
    return self.trustee_set.count()

  @property
  def last_alias_num(self):
    """
    FIXME: we should be tracking alias number, not the V* alias which then
    makes things a lot harder
    """
    if not self.use_voter_aliases:
      return None

    # FIXME: https://docs.djangoproject.com/en/dev/topics/db/multi-db/#database-routers
    # use database routes api to find proper database for the Voter model.
    # This will still work if someone deploys helios using only the default
    # database.
    SUBSTR_FUNCNAME = "substring"
    if 'sqlite' in settings.DATABASES['default']['ENGINE']:
        SUBSTR_FUNCNAME = "substr"

    return heliosutils.one_val_raw_sql("select max(cast(substr(alias, 2) as integer)) from " + Voter._meta.db_table + " where election_id = %s", [self.id]) or 0

  @property
  def departments_string(self):
    return "\n".join(self.departments or [])

  @property
  def trustees_string(self):
    helios_trustee = self.get_helios_trustee()
    trustees = [(t.name, t.email) for t in self.trustee_set.all() if t != helios_trustee]
    return "\n".join(["%s,%s" % (t[0], t[1]) for t in trustees])

  def update_answers(self):
    cands = sorted(self.candidates, key=lambda c: c['surname'])
    self.cands = cands
    answers = []
    for cand in cands:
      answers.append(u"%s %s %s [%s]" % (cand['surname'], cand['name'], cand['father_name'],
                             cand['department'].strip()))

    if not self.questions:
        question = {}
        question['answer_urls'] = [None for x in range(len(answers))]
        question['choice_type'] = 'stv'
        question['question'] = 'Candidates choice'
        question['answers'] = []
        question['result_type'] = 'absolute'
        question['tally_type'] = 'stv'
        self.questions = []
        self.questions.append(question)

    self.questions[0]['answers'] = answers
    self.save()

  @property
  def tallied(self):
    return self.workflow.tallied(self)

  @property
  def encrypted_tally_hash(self):
    return self.workflow.tally_hash(self)

  @property
  def is_archived(self):
    return self.archived_at != None

  @classmethod
  def get_featured(cls):
    return cls.objects.filter(featured_p = True).order_by('short_name')

  @classmethod
  def get_or_create(cls, **kwargs):
    return cls.objects.get_or_create(short_name = kwargs['short_name'], defaults=kwargs)

  @classmethod
  def get_by_user_as_admin(cls, user, archived_p=None, limit=None):
    query = cls.objects.filter(admins__in = [user])
    if archived_p == True:
      query = query.exclude(archived_at= None)
    if archived_p == False:
      query = query.filter(archived_at= None)
    query = query.order_by('-created_at')
    if limit:
      return query[:limit]
    else:
      return query

  @classmethod
  def get_by_user_as_voter(cls, user, archived_p=None, limit=None):
    query = cls.objects.filter(voter__user = user)
    if archived_p == True:
      query = query.exclude(archived_at= None)
    if archived_p == False:
      query = query.filter(archived_at= None)
    query = query.order_by('-created_at')
    if limit:
      return query[:limit]
    else:
      return query

  @classmethod
  def get_by_uuid(cls, uuid):
    try:
      return cls.objects.select_related().get(uuid=uuid)
    except cls.DoesNotExist:
      return None

  @classmethod
  def get_by_short_name(cls, short_name):
    try:
      return cls.objects.get(short_name=short_name)
    except cls.DoesNotExist:
      return None

  def add_voters_file(self, uploaded_file):
    """
    expects a django uploaded_file data structure, which has filename, content, size...
    """
    # now we're just storing the content
    # random_filename = str(uuid.uuid4())
    # new_voter_file.voter_file.save(random_filename, uploaded_file)

    new_voter_file = VoterFile(election = self,
                               voter_file_content = base64.encodestring(uploaded_file.read()))
    new_voter_file.save()

    self.append_log(ElectionLog.VOTER_FILE_ADDED)
    return new_voter_file

  def user_eligible_p(self, user):
    """
    Checks if a user is eligible for this election.
    """
    # registration closed, then eligibility doesn't come into play
    if not self.openreg:
      return False

    if self.eligibility == None:
      return True

    # is the user eligible for one of these cases?
    for eligibility_case in self.eligibility:
      if user.is_eligible_for(eligibility_case):
        return True

    return False

  def eligibility_constraint_for(self, user_type):
    if not self.eligibility:
      return []

    # constraints that are relevant
    relevant_constraints = [constraint['constraint'] for constraint in self.eligibility if constraint['auth_system'] == user_type]
    if len(relevant_constraints) > 0:
      return relevant_constraints[0]
    else:
      return []

  def eligibility_category_id(self, user_type):
    "when eligibility is by category, this returns the category_id"
    if not self.eligibility:
      return None

    constraint_for = self.eligibility_constraint_for(user_type)
    if len(constraint_for) > 0:
      constraint = constraint_for[0]
      return AUTH_SYSTEMS[user_type].eligibility_category_id(constraint)
    else:
      return None

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


  def voted_count(self):
    return self.voter_set.filter(vote__isnull=False).count()

  def step_created_completed(self):
    return bool(self.pk)

  def step_candidates_added_completed(self):
    return self.questions and len(self.questions) > 0

  def step_voters_added_completed(self):
    return self.voter_set.all().count() > 0

  def step_keys_generated_completed(self):
    return all([t.public_key for t in self.trustee_set.all()])

  def step_opened_completed(self):
    return bool(self.frozen_at)

  def step_voters_notified_completed(self):
    return bool(self.voter_set.filter(last_email_send_at__isnull=False).count())

  def step_closed_completed(self):
    return bool(self.voting_ended_at)

  @property
  def pretty_eligibility(self):
    if not self.eligibility:
      return "Anyone can vote."
    else:
      return_val = "<ul>"

      for constraint in self.eligibility:
        if constraint.has_key('constraint'):
          for one_constraint in constraint['constraint']:
            return_val += "<li>%s</li>" % AUTH_SYSTEMS[constraint['auth_system']].pretty_eligibility(one_constraint)
        else:
          return_val += "<li> any %s user</li>" % constraint['auth_system']

      return_val += "</ul>"

      return return_val

  def voting_has_started(self):
    """
    has voting begun? voting begins if the election is frozen, at the prescribed date or at the date that voting was forced to start
    """
    return self.frozen_at != None and (self.voting_starts_at == None or (datetime.datetime.now() >= (self.voting_started_at or self.voting_starts_at)))

  def voting_has_stopped(self):
    """
    has voting stopped? if tally computed, yes, otherwise if we have passed the date voting was manually stopped at,
    or failing that the date voting was extended until, or failing that the date voting is scheduled to end at.
    """
    voting_end = self.voting_ended_at or self.voting_extended_until or self.voting_ends_at
    return (voting_end != None and datetime.datetime.utcnow() >= voting_end) or \
        self.tallied

  def bad_mixnet(self):
    try:
      return self.mixnets.get(status="error")
    except ElectionMixnet.DoesNotExist:
      return None

  def mixnets_count(self):
      return self.mixnets.count()

  @property
  def issues_before_freeze(self):
    issues = []
    if self.questions == None or len(self.questions) == 0:
      issues.append(
        {'type': 'questions',
         'action': _("Add candidates to the election")}
        )

    trustees = Trustee.get_by_election(self)
    if len(trustees) == 0:
      issues.append({
          'type': 'trustees',
          'action': _("add at least one trustee")
          })

    for t in trustees:
      if t.public_key == None:
        issues.append({
            'type': 'trustee keypairs',
            'action': _('have trustee %s generate a keypair') % t.name
            })

      if t.last_verified_key_at == None:
        issues.append({
            'type': 'trustee verifications',
            'action': _('have trustee %s verify his key') % t.name
            })

    if self.voter_set.count() == 0 and not self.openreg:
      issues.append({
          "type" : "voters",
          "action" : _('enter your voter list (or open registration to the public)')
          })

    if self.workflow_type == "mixnet" and not self.mixnets_count():
      issues.append({
          "type" : "mixnet",
          "action" : _("setup election mixnets")
          })


    return issues

  def ready_for_tallying(self):
    return datetime.datetime.utcnow() >= self.tallying_starts_at

  def mix_next_mixnet(self):
    if self.is_mixing:
      raise Exception("Another mixing in process")

    if self.mixing_finished:
      raise Exception("Mixing finished")

    next_mixnet = self.mixnets.filter(status="pending")[0]
    next_mixnet.mix_ciphers()

  def compute_tally(self):
    """
    tally the election, assuming votes already verified
    """
    self.mix_next_mixnet()
    if self.mixing_finished and not self.encrypted_tally:
      self.store_encrypted_tally()
      self.save()

  def store_encrypted_tally(self):
    ciphers = self.zeus_election.get_mixed_ballots()
    tally_dict = {'num_tallied': len(ciphers), 'tally': [
      [{'alpha':c[0], 'beta':c[1]} for c in ciphers]]}
    tally = LDObject.fromDict(tally_dict, type_hint='phoebus/Tally')
    self.encrypted_tally = tally
    self.save()

  def ready_for_decryption_combination(self):
    """
    do we have a tally from all trustees?
    """
    for t in Trustee.get_by_election(self):
      if not t.decryption_factors:
        return False

    return True

  def generate_voters_hash(self):
    """
    look up the list of voters, make a big file, and hash it
    """

    # FIXME: for now we don't generate this voters hash:
    return

    if self.openreg:
      self.voters_hash = None
    else:
      voters = Voter.get_by_election(self)
      voters_json = utils.to_json([v.toJSONDict() for v in voters])
      self.voters_hash = utils.hash_b64(voters_json)

  def increment_voters(self):
    ## FIXME
    return 0

  def increment_cast_votes(self):
    ## FIXME
    return 0

  def set_eligibility(self):
    """
    if registration is closed and eligibility has not been
    already set, then this call sets the eligibility criteria
    based on the actual list of voters who are already there.

    This helps ensure that the login box shows the proper options.

    If registration is open but no voters have been added with password,
    then that option is also canceled out to prevent confusion, since
    those elections usually just use the existing login systems.
    """

    # don't override existing eligibility
    if self.eligibility != None:
      return

    # enable this ONLY once the cast_confirm screen makes sense
    #if self.voter_set.count() == 0:
    #  return

    auth_systems = copy.copy(settings.AUTH_ENABLED_AUTH_SYSTEMS)
    voter_types = [r['user__user_type'] for r in self.voter_set.values('user__user_type').distinct() if r['user__user_type'] != None]

    # password is now separate, not an explicit voter type
    if self.voter_set.filter(user=None).count() > 0:
      voter_types.append('password')
    else:
      # no password users, remove password from the possible auth systems
      if 'password' in auth_systems:
        auth_systems.remove('password')

    # closed registration: limit the auth_systems to just the ones
    # that have registered voters
    if not self.openreg:
      auth_systems = [vt for vt in voter_types if vt in auth_systems]

    self.eligibility = [{'auth_system': auth_system} for auth_system in auth_systems]
    self.save()

  def get_short_url(self):
      return "/helios/e/%s" % self.short_name

  def get_url(self):
      return "/helios/elections/%s/view" % self.uuid

  def freeze(self):
    """
    election is frozen when the voter registration, questions, and trustees are finalized
    """
    if len(self.issues_before_freeze) > 0:
      raise Exception("cannot freeze an election that has issues")

    self.frozen_at = datetime.datetime.utcnow()
    # voters hash
    self.generate_voters_hash()
    self.set_eligibility()
    self.zeus_election.validate_creating()
    # log it
    self.append_log(ElectionLog.FROZEN)
    self.save()

  @property
  def mixing_finished(self):
    mixnets = self.mixnets.filter(status="finished").count()
    return (mixnets > 0) and (mixnets == self.mixnets.count())

  @property
  def completed(self):
    return bool(self.result)

  @property
  def is_mixing(self):
      return bool(self.mixnets.filter(status="mixing").count())

  def generate_helios_mixnet(self, params={}):
    if self.tallied:
      raise Exception("Election tallied, cannot add additional mixnet")

    if self.is_mixing:
      raise Exception("Mixing already started, cannot add additional mixnet")

    params.update({'election': self})
    mixnets_count = self.mixnets.count()
    params.update({'mix_order':mixnets_count})
    mixnet = ElectionMixnet(**params)
    mixnet.save()

  @property
  def zeus_stage(self):
    if not self.pk or not self.frozen_at:
      return 'CREATING'

    if not self.voting_ended_at:
      return 'VOTING'

    if not self.mixing_finished:
      return 'MIXING'

    if not self.result:
      return 'DECRYPTING'

    return 'FINISHED'

  _zeus_election = None

  @property
  def zeus_election(self):
    if self._zeus_election and self._zeus_election.do_get_stage() == self.zeus_stage:
      return self._zeus_election

    from zeus import helios_election
    obj = helios_election.HeliosElection(uuid=self.uuid)
    obj.do_set_stage(self.zeus_stage)
    self._zeus_election = obj
    return obj

  def reprove_trustee(self, trustee):
      public_key = trustee.public_key
      pok = trustee.pok
      self.zeus_election.reprove_trustee(public_key.y, [pok.commitment,
                                                         pok.challenge,
                                                         pok.response])

      trustee.last_verified_key_at = datetime.datetime.now()
      trustee.save()

  def add_trustee_pk(self, trustee, public_key, pok):
    trustee.public_key = public_key
    trustee.pok = pok
    trustee.public_key_hash = utils.hash_b64(
        utils.to_json(
            trustee.public_key.toJSONDict()))
    trustee.save()
    # verify the pok

    self.zeus_election.add_trustee(trustee.public_key.y, [pok.commitment,
                                                         pok.challenge,
                                                         pok.response])

  def add_trustee_factors(self, trustee, factors, proofs):
    trustee.decryption_factors = factors
    trustee.decryption_proofs = proofs
    modulus, generator, order = self.zeus_election.do_get_cryptosystem()
    zeus_factors = self.zeus_election._get_zeus_factors(trustee)
    # zeus add_trustee_factors requires some extra info
    zeus_factors = {'trustee_public': trustee.public_key.y,
                    'decryption_factors': zeus_factors,
                    'modulus': modulus,
                    'generator': generator,
                    'order': order}
    self.zeus_election.add_trustee_factors(zeus_factors)
    trustee.save()

    if self.ready_for_decryption_combination():
      from helios import tasks
      tasks.tally_decrypt(self.pk)

  def _get_zeus_vote(self, enc_vote, voter=None, audit_password=None):
    answer = enc_vote.encrypted_answers[0]
    cipher = answer.choices[0]
    alpha, beta = cipher.alpha, cipher.beta
    modulus, generator, order = self.zeus_election.do_get_cryptosystem()
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
          'public': self.public_key.y
      }
    }

    if hasattr(answer, 'answers'):
      zeus_vote['audit_code'] = audit_password
      zeus_vote['voter_secret'] = answer.randomness[0]

    if audit_password:
      zeus_vote['audit_code'] = audit_password

    if voter:
      zeus_vote['voter'] = voter.uuid

    return zeus_vote

  def cast_vote(self, voter, enc_vote, audit_password=None):
    zeus_vote = self._get_zeus_vote(enc_vote, voter, audit_password)
    return self.zeus_election.cast_vote(zeus_vote)

  def generate_trustee(self):
    """
    generate a trustee including the secret key,
    thus a helios-based trustee
    """

    if self.get_helios_trustee():
        return self.get_helios_trustee()

    self.zeus_election.create_zeus_key()
    return self.get_helios_trustee()

  def get_helios_trustee(self):
    trustees_with_sk = self.trustee_set.exclude(secret_key = None)
    if len(trustees_with_sk) > 0:
      return trustees_with_sk[0]
    else:
      return None

  @property
  def workflow(self):
    return get_workflow_module(self.workflow_type)

  def has_helios_trustee(self):
    return self.get_helios_trustee() != None

  def helios_trustee_decrypt(self):
    self.zeus_election.compute_zeus_factors()

  def append_log(self, text):
    item = ElectionLog(election = self, log=text, at=datetime.datetime.utcnow())
    item.save()
    return item

  def get_log(self):
    return self.electionlog_set.order_by('-at')

  @property
  def url(self):
    return helios.views.get_election_url(self)

  def init_encrypted_tally(self):
      answers = self.last_mixed_mixnet.mixed_answers.get(question=0).mixed_answers.answers
      tally = self.init_tally()
      tally.tally = [[]]
      tally.tally[0] = [a.choice for a in answers]
      self.encrypted_tally = tally
      self.save()

  def init_tally(self):
    return self.workflow.Tally(election=self)

  @property
  def registration_status_pretty(self):
    if self.openreg:
      return "Open"
    else:
      return "Closed"

  @classmethod
  def one_question_winner(cls, question, result, num_cast_votes):
    """
    determining the winner for one question
    """
    # sort the answers , keep track of the index
    counts = sorted(enumerate(result), key=lambda(x): x[1])
    counts.reverse()

    the_max = question['max'] or 1
    the_min = question['min'] or 0

    # if there's a max > 1, we assume that the top MAX win
    if the_max > 1:
      return [c[0] for c in counts[:the_max]]

    # if max = 1, then depends on absolute or relative
    if question['result_type'] == 'absolute':
      if counts[0][1] >=  (num_cast_votes/2 + 1):
        return [counts[0][0]]
      else:
        return []
    else:
      # assumes that anything non-absolute is relative
      return [counts[0][0]]

  def ecounting_dict(self):
    schools = []
    for school in self.departments:
      candidates = []
      for i, candidate in enumerate(self.candidates):
        if candidate['department'] != school:
          continue

        candidate_entry = {
          'candidateTmpId': str(i+1),
          'firstName': candidate['name'],
          'lastName': candidate['surname'],
          'fatherName': candidate['father_name']
        }

        candidates.append(candidate_entry)

      school_entry = {
        'Name': school,
        'candidates': candidates
      }
      schools.append(school_entry)

    ballots = []
    for i, ballot in enumerate(self.pretty_result['candidates_selections']):
      ballot_votes = []
      for j, selection in enumerate(ballot):
        vote_entry = {
          'rank': j + 1,
          'candidateTmpId': selection['selection_index']
        }
        ballot_votes.append(vote_entry)

      ballot_entry = {
        'ballotSerialNumber': str(i+1),
        'votes': ballot_votes
      }
      ballots.append(ballot_entry)

    data = {
      'elName': self.name,
      'elDescription': self.description,
      'numOfRegisteredVoters': self.voter_set.count(),
      'numOfCandidates': len(self.candidates),
      'numOfEligibles': self.eligibles_count,
      'hasLimit': 1 if self.has_department_limit else 0,
      'schools': schools,
      'ballots': ballots
    }
    return data

  @property
  def winners(self):
    """
    Depending on the type of each question, determine the winners
    returns an array of winners for each question, aka an array of arrays.
    assumes that if there is a max to the question, that's how many winners there are.
    """
    return [self.one_question_winner(self.questions[i], self.result[i], self.num_cast_votes) for i in range(len(self.questions))]

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

def csv_reader(csv_data, **kwargs):
    if not isinstance(csv_data, str):
        m = "Please provide string data to csv_reader, not %s" % type(csv_data)
        raise ValueError(m)
    all_encodings = ['utf-8', 'utf-16', 'utf-16le', 'utf-16be', 'iso-8859-7']
    all_encodings.reverse()
    for line in csv_data.splitlines():
      encodings = list(all_encodings)
      if not line.strip():
        continue

      while 1:
          if not encodings:
            m = "Cannot decode csv data!"
            raise ValueError(m)
          encoding = encodings[-1]
          try:
            cells = line.split(',', 3)
            if len(cells) < 3:
                cells = line.split(';')
                if len(cells) < 3:
                    m = ("CSV must have at least 3 fields "
                         "(email, last_name, name)")
                    raise ValueError(m)
                cells += [u''] * (4 - len(cells))
            yield [cell.decode(encoding) for cell in cells]
            break
          except UnicodeDecodeError, e:
            encodings.pop()
            continue

class VoterFile(models.Model):
  """
  A model to store files that are lists of voters to be processed
  """
  # path where we store voter upload
  PATH = settings.VOTER_UPLOAD_REL_PATH

  election = models.ForeignKey(Election)

  # we move to storing the content in the DB
  voter_file = models.FileField(upload_to=PATH, max_length=250,null=True)
  voter_file_content = models.TextField(null=True)

  uploaded_at = models.DateTimeField(auto_now_add=True)
  processing_started_at = models.DateTimeField(auto_now_add=False, null=True)
  processing_finished_at = models.DateTimeField(auto_now_add=False, null=True)
  num_voters = models.IntegerField(null=True)

  def itervoters(self):
    if self.voter_file_content:
      voter_data = base64.decodestring(self.voter_file_content)
    else:
      voter_data = open(self.voter_file.path, "r").read()

    reader = csv_reader(voter_data)

    for voter_fields in reader:
      # bad line
      if len(voter_fields) < 1:
        continue

      return_dict = {'voter_id': voter_fields[0]}

      if len(voter_fields) > 0:
        validate_email(voter_fields[0])
        return_dict['email'] = voter_fields[0]

      if len(voter_fields) > 1:
        if voter_fields[1].strip() == "":
          raise ValidationError(_("Name cannot be empty"))

        return_dict['name'] = voter_fields[1]

      if len(voter_fields) > 2:

        if voter_fields[1].strip() == "":
          raise ValidationError(_("Surname cannot be empty"))

        return_dict['surname'] = voter_fields[2]

      if len(voter_fields) > 3:
        return_dict['fathername'] = voter_fields[3]

      yield return_dict

  def process(self):
    self.processing_started_at = datetime.datetime.utcnow()
    self.save()

    election = self.election

    # now we're looking straight at the content
    if self.voter_file_content:
      voter_data = base64.decodestring(self.voter_file_content)
    else:
      voter_data = open(self.voter_file.path, "r").read()

    reader = csv_reader(voter_data)

    last_alias_num = election.last_alias_num

    num_voters = 0
    new_voters = []
    for voter in reader:
      # bad line
      if len(voter) < 1:
        continue

      num_voters += 1
      voter_id = voter[0].strip()
      name = voter_id
      email = voter_id
      fathername = ""

      if len(voter) > 0:
        email = voter[0].strip()

      if len(voter) > 1:
        name = voter[1].strip()

      if len(voter) > 2:
        surname = voter[2].strip()

      if len(voter) > 3:
        fathername = voter[3].strip()

      # create the user -- NO MORE
      # user = User.update_or_create(user_type='password', user_id=email, info = {'name': name})

      # does voter for this user already exist
      voter = Voter.get_by_election_and_voter_id(election, voter_id)

      # create the voter
      if not voter:
        voter_uuid = str(uuid.uuid4())
        voter = Voter(uuid= voter_uuid, user = None, voter_login_id = voter_id,
                      voter_name = name, voter_email = email, election = election,
                      voter_surname=surname, voter_fathername=fathername)
        voter.init_audit_passwords()
        voter.generate_password()
        new_voters.append(voter)
        voter.save()

      else:
        voter.voter_name = name
        voter.voter_surname = surname
        voter.voter_fathername = fathername
        voter.save()

    if election.use_voter_aliases:
      voter_alias_integers = range(last_alias_num+1, last_alias_num+1+num_voters)
      random.shuffle(voter_alias_integers)
      for i, voter in enumerate(new_voters):
        voter.alias = 'V%s' % voter_alias_integers[i]
        voter.save()

    self.num_voters = num_voters
    self.processing_finished_at = datetime.datetime.utcnow()
    self.save()

    return num_voters



class Voter(HeliosModel):
  election = models.ForeignKey(Election)

  uuid = models.CharField(max_length = 50)

  # for users of type password, no user object is created
  # but a dynamic user object is created automatically
  user = models.ForeignKey('heliosauth.User', null=True)

  # if user is null, then you need a voter login ID and password
  voter_login_id = models.CharField(max_length = 100, null=True)
  voter_password = models.CharField(max_length = 100, null=True)
  voter_name = models.CharField(max_length = 200, null=True)
  voter_surname = models.CharField(max_length = 200, null=True)
  voter_email = models.CharField(max_length = 250, null=True)
  voter_fathername = models.CharField(max_length = 250, null=True)

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

  last_email_send_at = models.DateTimeField(null=True)

  class Meta:
    unique_together = (('election', 'voter_login_id'))

  def __init__(self, *args, **kwargs):
    super(Voter, self).__init__(*args, **kwargs)

    # stub the user so code is not full of IF statements
    if not self.user:
      self.user = User(user_type='password', user_id=self.voter_email, name=self.voter_name)


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
      return settings.URL_HOST + "/helios/elections/%s/l/%s/%s" % (self.election.uuid, self.uuid, self.voter_password)

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
    if election.use_voter_aliases:
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
      return cls.objects.get(election = election, voter_login_id = voter_id)
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
    return self.user.name

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
    if self.voter_password:
      raise Exception("password already exists")

    self.voter_password = heliosutils.random_string(length)

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


class CastVote(HeliosModel):
  # the reference to the voter provides the voter_uuid
  voter = models.ForeignKey(Voter)
  election = models.ForeignKey(Election)

  previous = models.CharField(max_length=255, default="")

  # the actual encrypted vote
  vote = LDObjectField(type_hint = 'phoebus/EncryptedVote')

  # cache the hash of the vote
  vote_hash = models.CharField(max_length=100)

  # a tiny version of the hash to enable short URLs
  vote_tinyhash = models.CharField(max_length=50, null=True, unique=True)

  cast_at = models.DateTimeField(auto_now_add=True)
  audit_code = models.CharField(max_length=100, null=True)

  # some ballots can be quarantined (this is not the same thing as provisional)
  quarantined_p = models.BooleanField(default=False, null=False)
  released_from_quarantine_at = models.DateTimeField(auto_now_add=False, null=True)

  # when is the vote verified?
  verified_at = models.DateTimeField(null=True)
  invalidated_at = models.DateTimeField(null=True)
  fingerprint = models.CharField(max_length=255)
  signature = JSONField(null=True)
  index = models.PositiveIntegerField(null=True)

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

  @classmethod
  def get_by_voter(cls, voter):
    return cls.objects.filter(voter = voter).order_by('-cast_at')

  def verify_and_store(self):
    # if it's quarantined, don't let this go through
    if self.is_quarantined:
      raise Exception("cast vote is quarantined, verification and storage is delayed.")

    result = self.vote.verify(self.voter.election)

    if result:
      self.verified_at = datetime.datetime.utcnow()
    else:
      self.invalidated_at = datetime.datetime.utcnow()

    # save and store the vote as the voter's last cast vote
    self.save()

    if result:
      self.voter.store_vote(self)

    return result

  def issues(self, election):
    """
    Look for consistency problems
    """
    issues = []

    # check the election
    if self.vote.election_uuid != election.uuid:
      issues.append("the vote's election UUID does not match the election for which this vote is being cast")

    return issues

class AuditedBallot(models.Model):
  """
  ballots for auditing
  """
  election = models.ForeignKey(Election)
  voter = models.ForeignKey(Voter, null=True)
  raw_vote = models.TextField()
  vote_hash = models.CharField(max_length=100)
  added_at = models.DateTimeField(auto_now_add=True)
  fingerprint = models.CharField(max_length=255)
  audit_code = models.CharField(max_length=100)
  is_request = models.BooleanField(default=True)
  signature = JSONField(null=True)

  @classmethod
  def get(cls, election, vote_hash):
    return cls.objects.get(election = election, vote_hash = vote_hash)

  @classmethod
  def get_by_election(cls, election, after=None, limit=None):
    query = cls.objects.filter(election = election).order_by('vote_hash')

    # if we want the list after a certain UUID, add the inequality here
    if after:
      query = query.filter(vote_hash__gt = after)

    if limit:
      query = query[:limit]

    return query

  class Meta:
    unique_together = (('election','is_request','fingerprint'))

class Trustee(HeliosModel):
  election = models.ForeignKey(Election)

  uuid = models.CharField(max_length=50)
  name = models.CharField(max_length=200)
  email = models.EmailField()
  secret = models.CharField(max_length=100)

  # public key
  public_key = LDObjectField(type_hint = 'legacy/EGPublicKey',
                             null=True)
  public_key_hash = models.CharField(max_length=100)

  # secret key
  # if the secret key is present, this means
  # Helios is playing the role of the trustee.
  secret_key = LDObjectField(type_hint = 'legacy/EGSecretKey',
                             null=True)

  # proof of knowledge of secret key
  pok = LDObjectField(type_hint = 'legacy/DLogProof',
                      null=True)

  # decryption factors
  decryption_factors = LDObjectField(type_hint = datatypes.arrayOf(datatypes.arrayOf('core/BigInteger')),
                                     null=True)

  decryption_proofs = LDObjectField(type_hint = datatypes.arrayOf(datatypes.arrayOf('legacy/EGZKProof')),
                                    null=True)

  last_verified_key_at = models.DateTimeField(null=True)

  def save(self, *args, **kwargs):
    """
    override this just to get a hook
    """
    # not saved yet?
    if not self.secret:
      self.secret = heliosutils.random_string(12)
      self.election.append_log("Trustee %s added" % self.name)

    super(Trustee, self).save(*args, **kwargs)

  def get_login_url(self):
    from django.core.urlresolvers import reverse
    from helios.views import trustee_login
    url = settings.SECURE_URL_HOST + reverse(trustee_login,
                                               args=[self.election.short_name,
                                                     self.email,
                                                     self.secret])
    return url

  def send_url_via_mail(self):

    url = self.get_login_url()

    body = _("""
    You are a trustee for %(election_name)s.

    Your trustee dashboard is at

      %(url)s

    --
    Helios
             """) % {'election_name': self.election.name, 'url': url}

    send_mail(_('your trustee homepage for %(election_name)s') % {'election_name': self.election.name},
              body,
              settings.SERVER_EMAIL,
              ["%s <%s>" % (self.name, self.email)],
              fail_silently=True)

  @classmethod
  def get_by_election(cls, election):
    return cls.objects.filter(election = election)

  @classmethod
  def get_by_uuid(cls, uuid):
    return cls.objects.get(uuid = uuid)

  @classmethod
  def get_by_election_and_uuid(cls, election, uuid):
    return cls.objects.get(election = election, uuid = uuid)

  @classmethod
  def get_by_election_and_email(cls, election, email):
    try:
      return cls.objects.get(election = election, email = email)
    except cls.DoesNotExist:
      return None

  @property
  def datatype(self):
    return self.election.datatype.replace('Election', 'Trustee')

  def verify_decryption_proofs(self):
    """
    verify that the decryption proofs match the tally for the election
    """
    return self.election.workflow.verify_encryption_proof(self.election, self)

