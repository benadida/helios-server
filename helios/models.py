# -*- coding: utf-8 -*-
"""
Data Objects for Helios.

Ben Adida
(ben@adida.net)
"""

from django.db import models, transaction
import json
from django.conf import settings
from django.core.mail import send_mail

import datetime
import logging
import uuid
import random
import io
import bleach

import csv
import copy
import itertools
import unicodecsv

from validate_email import validate_email

from crypto import algs, elgamal, utils, electionalgs, thresholdalgs
from helios import utils as heliosutils
import helios.views

from helios import datatypes

# useful stuff in helios_auth
from helios_auth.models import User, AUTH_SYSTEMS
from helios_auth.jsonfield import JSONField
from helios.datatypes.djangofield import LDObjectField

from operator import itemgetter
from helios.constants import p, g, q, ground_1, ground_2

# parameters for everything
ELGAMAL_PARAMS = elgamal.Cryptosystem()

# trying new ones from OlivierP
ELGAMAL_PARAMS.p = p
ELGAMAL_PARAMS.q = q

ELGAMAL_PARAMS.g = g


class HeliosModel(models.Model, datatypes.LDObjectContainer):
    class Meta:
        abstract = True


class Election(HeliosModel):
    admin = models.ForeignKey(User)

    uuid = models.CharField(max_length=50, null=False)

    # keep track of the type and version of election, which will help dispatch to the right
    # code, both for crypto and serialization
    # v3 and prior have a datatype of "legacy/Election"
    # v3.1 will still use legacy/Election
    # later versions, at some point will upgrade to "2011/01/Election"
    datatype = models.CharField(max_length=250, null=False, default="legacy/Election")

    short_name = models.CharField(max_length=100)
    name = models.CharField(max_length=250)

    ELECTION_TYPES = (
        ('election', 'Election'),
        ('referendum', 'Referendum')
    )

    election_type = models.CharField(max_length=250, null=False, default='election', choices=ELECTION_TYPES)
    private_p = models.BooleanField(default=False, null=False)

    description = models.TextField()
    public_key = LDObjectField(type_hint='legacy/EGPublicKey', null=True)
    private_key = LDObjectField(type_hint='legacy/EGSecretKey', null=True)

    questions = LDObjectField(type_hint='legacy/Questions', null=True)

    # eligibility is a JSON field, which lists auth_systems and eligibility details for that auth_system, e.g.
    # [{'auth_system': 'cas', 'constraint': [{'year': 'u12'}, {'year':'u13'}]}, {'auth_system' : 'password'}, {'auth_system' : 'openid', 'constraint': [{'host':'http://myopenid.com'}]}]
    eligibility = LDObjectField(type_hint='legacy/Eligibility', null=True)

    # open registration?
    # this is now used to indicate the state of registration,
    # whether or not the election is frozen
    openreg = models.BooleanField(default=False)

    # featured election?
    featured_p = models.BooleanField(default=False)

    # voter aliases?
    use_voter_aliases = models.BooleanField(default=False)

    # auditing is not for everyone
    use_advanced_audit_features = models.BooleanField(default=True, null=False)

    # randomize candidate order?
    randomize_answer_order = models.BooleanField(default=False, null=False)

    # where votes should be cast
    cast_url = models.CharField(max_length=500)

    # dates at which this was touched
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now_add=True)

    # dates at which things happen for the election
    frozen_at = models.DateTimeField( auto_now_add=False, default=None, null=True)
    archived_at = models.DateTimeField( auto_now_add=False, default=None, null=True)

    use_threshold = models.BooleanField(default=True)
    frozen_trustee_list = models.BooleanField(default=False)
    encrypted_shares_uploaded = models.BooleanField(default=False)

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

    # we want to explicitly release results
    result_released_at = models.DateTimeField(auto_now_add=False, default=None, null=True)

    # the hash of all voters (stored for large numbers)
    voters_hash = models.CharField(max_length=100, null=True)

    # encrypted tally, each a JSON string
    # used only for homomorphic tallies
    encrypted_tally = LDObjectField(type_hint='legacy/Tally', null=True)

    # results of the election
    result = LDObjectField(type_hint='legacy/Result', null=True)

    # decryption proof, a JSON object
    # no longer needed since it's all trustees
    result_proof = JSONField(null=True)

    # help email
    help_email = models.EmailField(null=True)

    # downloadable election info
    election_info_url = models.CharField(max_length=300, null=True)

    # metadata for the election
    @property
    def metadata(self):
        return {
            'help_email': self.help_email or 'help@heliosvoting.org',
            'private_p': self.private_p,
            'use_advanced_audit_features': self.use_advanced_audit_features,
            'randomize_answer_order': self.randomize_answer_order
        }

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

        return heliosutils.one_val_raw_sql("select max(cast(substring(alias, 2) as integer)) from " + Voter._meta.db_table + " where election_id = %s", [self.id]) or 0

    @property
    def encrypted_tally_hash(self):
        if not self.encrypted_tally:
            return None

        return utils.hash_b64(self.encrypted_tally.toJSON())

    @property
    def is_archived(self):
        return self.archived_at != None

    @property
    def description_bleached(self):
        return bleach.clean(self.description, tags = bleach.ALLOWED_TAGS + ['p', 'h4', 'h5', 'h3', 'h2', 'br'])

    @classmethod
    def get_featured(cls):
        return cls.objects.filter(featured_p=True).order_by('short_name')

    @classmethod
    def get_or_create(cls, **kwargs):
        return cls.objects.get_or_create(short_name=kwargs['short_name'], defaults=kwargs)

    @classmethod
    def get_by_user_as_admin(cls, user, archived_p=None, limit=None):
        query = cls.objects.filter(admin=user)
        if archived_p == True:
            query = query.exclude(archived_at=None)
        if archived_p == False:
            query = query.filter(archived_at=None)
        query = query.order_by('-created_at')
        if limit:
            return query[:limit]
        else:
            return query

    @classmethod
    def get_by_user_as_voter(cls, user, archived_p=None, limit=None):
        query = cls.objects.filter(voter__user=user)
        if archived_p == True:
            query = query.exclude(archived_at=None)
        if archived_p == False:
            query = query.filter(archived_at=None)
        query = query.order_by('-created_at')
        if limit:
            return query[:limit]

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

        new_voter_file = VoterFile(election=self, voter_file_content=uploaded_file.read())
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
        relevant_constraints = [constraint['constraint'] for constraint in self.eligibility if constraint['auth_system'] == user_type and constraint.has_key('constraint')]
        if len(relevant_constraints) > 0:
            return relevant_constraints[0]
        else:
            return []

    def eligibility_category_id(self, user_type):
        """
        when eligibility is by category, this returns the category_id
        """
        if not self.eligibility:
            return None

        constraint_for = self.eligibility_constraint_for(user_type)
        if len(constraint_for) > 0:
            constraint = constraint_for[0]
            return AUTH_SYSTEMS[user_type].eligibility_category_id(constraint)
        else:
            return None

    @property
    def pretty_eligibility(self):
        if not self.eligibility:
            return 'Anyone!'
        else:
            i = 0

            return_val = ""
            for constraint in self.eligibility:
                if len(self.eligibility) > 1:
                    return_val += "%i. " % i + 1

                if constraint.has_key('constraint'):
                    for one_constraint in constraint['constraint']:
                        return_val += "%s" % AUTH_SYSTEMS[constraint['auth_system']].pretty_eligibility(one_constraint)
                else:
                    return_val += "Any %s user" % constraint['auth_system'].capitalize()

                i += 1
                if i < len(self.eligibility):
                    return_val += """<i class="spacer"></i>"""

            return return_val

    def voting_has_started(self):
        """
        has voting begun? voting begins if the election is frozen, at the prescribed date or at the date that voting was forced to start
        """
        if not self.voting_started_at and not self.voting_starts_at:
            return True

        voting_started_at = False
        if self.voting_started_at:
            voting_started_at = datetime.datetime.utcnow() >= self.voting_started_at

        voting_stars_at = False
        if self.voting_starts_at:
            voting_starts_at = datetime.datetime.now() >= self.voting_starts_at

        return self.frozen_at and (voting_started_at or voting_starts_at)

    def voting_has_stopped(self):
        """
        has voting stopped? if tally computed, yes, otherwise if we have passed the date voting was manually stopped at,
        or failing that the date voting was extended until, or failing that the date voting is scheduled to end at.
        """
        voting_ended_at = False
        if self.voting_ended_at:
            voting_ended_at = datetime.datetime.utcnow() >= self.voting_ended_at

        voting_ends_at = False
        if self.voting_ends_at:
            voting_ends_at = datetime.datetime.now() >= self.voting_ends_at

        voting_extended_until = False
        if self.voting_extended_until:
            voting_extended_until = datetime.datetime.now() >= self.voting_extended_until

        return self.encrypted_tally or (voting_ended_at or voting_ends_at or voting_extended_until)

    @property
    def issues_before_freeze(self):
        issues = []
        
        trustees = Trustee.get_by_election(self)
        if len(trustees) == 0:
            issues.append({
                'type': 'trustees',
                'action': "Add at least one trustee."
            })

        for t in trustees:
            if t.public_key == None:
                if not self.use_threshold:
                    issues.append({
                        'type': 'trustee keypairs',
                        'action': 'Have trustee %s generate a key pair.' % t.name
                    })
                else:
                    if t != self.get_helios_trustee():
                        issues.append({
                            'type': 'trustee keypairs',
                            'action': 'Wait for trustee %s to complete the key ceremony.' % t.name
                        })

        if self.questions == None or len(self.questions) == 0:
            issues.append(
                {'type': 'questions',
                 'action': "Add questions to the ballot."}
            )

        if self.voter_set.count() == 0 and not self.openreg:
            issues.append({
                "type": "voters",
                "action": 'Enter your voter list (or open registration to the public).'
            })

        return issues

    def ready_for_tallying(self):
        return datetime.datetime.utcnow() >= self.tallying_starts_at

    def compute_tally(self):
        """
        tally the election, assuming votes already verified
        """
        tally = self.init_tally()
        for voter in self.voter_set.exclude(vote=None):
          tally.add_vote(voter.vote, verify_p=False)

        self.encrypted_tally = tally
        self.save()

    def ready_for_decryption(self):
        return self.encrypted_tally != None

    def ready_for_decryption_combination(self):
        """
        do we have a tally from all trustees?
        """
        k = None
        count = 0

        scheme = self.get_scheme()
        if scheme:
            k = scheme.k

        trustees = Trustee.get_by_election(self)
        for t in trustees:
            if t.decryption_factors:
                count = count + 1

        if self.use_threshold:
            if k and count >= k:
                return True
            else:
                return False
        else:
            if count == len(trustees):
                return True
            else:
                return False

        return True

    def release_result(self):
      """
      release the result that should already be computed
      """
      if not self.result:
        return

      self.result_released_at = datetime.datetime.utcnow()

    def combine_decryptions(self):
        """
        combine all of the decryption results
        """

        # gather the decryption factors
        trustees = Trustee.get_by_election(self)
        decryption_factors = [t.decryption_factors for t in trustees]

        if self.use_threshold:
            decryption_factors = []
            scheme = self.get_scheme()
            trustees_active = Trustee.objects.filter(election=self).exclude(decryption_factors=None)
            x_values = [t.id for t in trustees_active]
            if len(trustees_active) >= scheme.k:
                for i in range(scheme.k):
                    numerator = 1
                    denominator = 1
                    xi = x_values[i]
                    for j in range(scheme.k):
                        xj = x_values[j]
                        if xi != xj:
                            numerator = (numerator * -xj) % q
                            denominator = (denominator * (xi - xj)) % q

                    lambda_now = (numerator * algs.Utils.inverse(denominator, q)) % q

                    trustee = trustees_active[i]
                    nof_questions = len(trustee.decryption_factors)
                    decryption_factors.append([[pow(trustee.decryption_factors[question][answer], lambda_now, p) for answer in range(len(trustee.decryption_factors[question]))] for question in range(nof_questions)])

        self.result = self.encrypted_tally.decrypt_from_factors(decryption_factors, self.public_key)
        self.append_log(ElectionLog.DECRYPTIONS_COMBINED)
        self.save()

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
        # FIXME
        return 0

    def increment_cast_votes(self):
        # FIXME
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
        # if self.voter_set.count() == 0:
        #  return

        auth_systems = copy.copy(settings.AUTH_ENABLED_AUTH_SYSTEMS)
        voter_types = [r['user__user_type'] for r in self.voter_set.values('user__user_type').distinct() if r['user__user_type'] != None]

        # password is now separate, not an explicit voter type
        if self.voter_set.filter(user=None).count() > 0:
            voter_types.append('password')
        else:
            # no password users, remove password from the possible helios_auth
            # systems
            if 'password' in auth_systems:
                auth_systems.remove('password')

        # closed registration: limit the auth_systems to just the ones
        # that have registered voters
        if not self.openreg:
            auth_systems = [vt for vt in voter_types if vt in auth_systems]

        self.eligibility = [{'auth_system': auth_system} for auth_system in auth_systems]
        self.save()

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

        # public key for trustees
        trustees = Trustee.get_by_election(self)

        combined_pk = None
        if self.use_threshold:
            k = 0

            scheme = self.get_scheme()
            if scheme:
                k = scheme.k

            for t in trustees[0:k]:
                xi = t.id
                numerator = 1
                denominator = 1
                for j in range(k):
                    xj = trustees[j].id
                    if xi != xj:
                        numerator = (numerator * -xj) % q
                        denominator = (denominator * (xi - xj)) % q

                lambda_t = (numerator * algs.Utils.inverse(denominator, q)) % q

                if combined_pk == None:
                    combined_pk = t.public_key
                    combined_pk.y = pow(combined_pk.y, lambda_t, p)
                else:
                    combined_pk.y = (combined_pk.y * pow(t.public_key.y, lambda_t, p)) % p
        else:
            for t in trustees:
                if combined_pk == None:
                    combined_pk = t.public_key
                else:
                    combined_pk.y = (combined_pk.y * t.public_key.y) % p

        self.public_key = combined_pk

        # log it
        self.append_log(ElectionLog.FROZEN)

        self.save()

    def generate_trustee(self, params):
        """
        generate a trustee including the secret key,
        thus a helios-based trustee
        """

        # create the trustee
        trustee = Trustee(election=self)
        trustee.uuid = str(uuid.uuid4())
        trustee.name = settings.DEFAULT_FROM_NAME
        trustee.email = settings.DEFAULT_FROM_EMAIL
        trustee.helios_trustee = True

        if not self.use_threshold:
            keypair = params.generate_keypair()

            trustee.public_key = keypair.pk
            trustee.secret_key = keypair.sk

            # FIXME: is this at the right level of abstraction?
            trustee.public_key_hash = datatypes.LDObject.instantiate(trustee.public_key, datatype='legacy/EGPublicKey').hash

            trustee.pok = trustee.secret_key.prove_sk(algs.DLog_challenge_generator)

            trustee.save()
        else:
            if len(SecretKey.objects.all()) > 0:
                sk = SecretKey.objects.all()[0]
                key = sk.public_key

            else:
                key = Key()
                keypair = params.generate_keypair()
                key.name = trustee.name
                key.email = trustee.email
                key.public_key_encrypt = utils.to_json(keypair.pk.to_dict())
                key.pok_encrypt = keypair.sk.prove_sk(algs.DLog_challenge_generator)
                secret_key = SecretKey()
                secret_key.secret_key_encrypt = utils.to_json(keypair.sk.to_dict())
                keypair = params.generate_keypair()
                key.public_key_signing = utils.to_json(keypair.pk.to_dict())
                secret_key.secret_key_signing = utils.to_json(keypair.sk.to_dict())
                key.pok_signing = keypair.sk.prove_sk(algs.DLog_challenge_generator)
                key.public_key_encrypt_hash = utils.hash_b64(key.public_key_encrypt)
                key.public_key_signing_hash = utils.hash_b64(key.public_key_signing)
                key.save()
                secret_key.public_key = key
                secret_key.save()

            trustee.key = key
            trustee.save()

    def get_scheme(self):
        schemes = self.thresholdscheme_set.all()
        if len(schemes) == 1:
            scheme = schemes[0]
            return scheme
        else:
            return None

    def get_trustees(self):  # get trustees with uploaded pk
        trustees_with_pk = self.trustee_set.exclude(public_key=None)
        if len(trustees_with_pk) > 0:
            return trustees_with_pk
        else:
            return None

    def get_helios_trustee(self):
        helios_trustees = Trustee.objects.filter(helios_trustee=True).filter(election=self)
        if len(helios_trustees) > 0:
            return helios_trustees[0]
        else:
            return None

    def has_helios_trustee(self):
        return self.get_helios_trustee() != None

    def helios_trustee_decrypt(self):
        tally = self.encrypted_tally
        tally.init_election(self)

        trustee = self.get_helios_trustee()
        factors, proof = tally.decryption_factors_and_proofs(trustee.secret_key)

        trustee.decryption_factors = factors
        trustee.decryption_proofs = proof
        trustee.save()

    def trustees_added_communication_keys(self):
        trustees = Trustee.get_by_election(self)

        if len(trustees) == 0:
            trustees_added_communication_keys = False
        else:
            trustees_added_communication_keys = True
            for trustee in trustees:
                if not trustee.helios_trustee and not trustee.key:
                    trustees_added_communication_keys = False

        return trustees_added_communication_keys

    def trustees_added_encrypted_shares(self):
        trustees = Trustee.get_by_election(self)

        if len(trustees) == 0:
            trustees_added_encrypted_shares = False
        else:
            trustees_added_encrypted_shares = True
            for trustee in trustees:
                if not trustee.helios_trustee and not trustee.added_encrypted_shares:
                    trustees_added_encrypted_shares = False

        return trustees_added_encrypted_shares

    def trustees_added_public_keys(self):
        trustees = Trustee.get_by_election(self)

        if len(trustees) == 0:
            trustees_added_public_keys = False
        else:
            trustees_added_public_keys = True
            for trustee in trustees:
                if not trustee.public_key:
                    trustees_added_public_keys = False

        return trustees_added_public_keys

    def append_log(self, text):
        item = ElectionLog(
            election=self, log=text, at=datetime.datetime.utcnow())
        item.save()
        return item

    def get_log(self):
        return self.electionlog_set.order_by('-at')

    @property
    def url(self):
        return helios.views.get_election_url(self)

    def init_tally(self):
        # FIXME: create the right kind of tally
        from helios.workflows import homomorphic
        return homomorphic.Tally(election=self)

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
            if counts[0][1] >= (num_cast_votes / 2 + 1):
                return [counts[0][0]]
            else:
                return []
        else:
            # assumes that anything non-absolute is relative
            return [counts[0][0]]

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
        if not self.result:
            return None

        # get the winners
        winners = self.winners

        raw_result = self.result
        prettified_result = []

        # loop through questions
        for i in range(len(self.questions)):
            q = self.questions[i]
            pretty_question = []

            # go through answers
            for j in range(len(q['answers'])):
                a = q['answers'][j]
                count = raw_result[i][j]
                pretty_question.append({'answer': a, 'count': count, 'winner': (j in winners[i])})

            prettified_result.append({'question': q['short_name'], 'answers': pretty_question})

        return prettified_result

    def create_scheme(self, n, k, ground_1, ground_2):

        if len(self.thresholdscheme_set.all()) == 0:
            scheme = ThresholdScheme(election=self)
            scheme.n = n
            scheme.k = k
            scheme.ground_1 = ground_1
            scheme.ground_2 = ground_2
            scheme.save()

    def number_trustees(self):
        trustees = self.get_trustees()
        for i in range(len(trustees)):
            trustee = trustees[i]
            trustee.point_number = i + 1
            trustee.save()

    def check_all_received_points(self):
        trustees = self.get_trustees()
        verification_list = []
        for i in range(len(trustees)):
            trustee = trustees[i]
            for j in range(len(trustee.received_points)):
                inner_verification_list = []
                com_point = trustee.received_points[j]
                point_x = com_point.point.x_value
                trustee_sender = Trustee.get_by_pointnumber(point_x)
                test = com_point.verify_commitments()
                feedback_temp = Feedback(trustee_sender, test)
                trustee.feedback.append(feedback_temp)
                trustee.save()

    def combine_received_points(self, params):
        trustees = self.get_trustees()
        for i in range(len(trustees)):
            trustee = trustees[i]
            temp_sum = 0
            for j in range(len(trustee.received_points)):
                com_point = trustee.received_points[j]
                point = com_point.point
                temp_sum = temp_sum + point.y_value
            secret_key = temp_sum
            keypair = params.generate_keypair(secret_key)
            trustee.public_key = keypair.pk
            trustee.secret_key = keypair.sk
            trustee.save()


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
# UTF8 craziness for CSV
##


def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
        # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(utf_8_encoder(unicode_csv_data),
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        try:
            yield [unicode(cell, 'utf-8') for cell in row]
        except:
            yield [unicode(cell, 'latin-1') for cell in row]


def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        # FIXME: this used to be line.encode('utf-8'),
        # need to figure out why this isn't consistent
        yield line


class VoterFile(models.Model):
    """
    A model to store files that are lists of voters to be processed
    """
    # path where we store voter upload
    PATH = settings.VOTER_UPLOAD_REL_PATH

    election = models.ForeignKey(Election)

    # we move to storing the content in the DB
    voter_file = models.FileField(upload_to=PATH, max_length=250, null=True)
    voter_file_content = models.TextField(null=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)
    processing_started_at = models.DateTimeField(auto_now_add=False, null=True)
    processing_finished_at = models.DateTimeField(auto_now_add=False, null=True)
    num_voters = models.IntegerField(null=True)

    def itervoters(self):
        if self.voter_file_content:
            if type(self.voter_file_content) == unicode:
                content = self.voter_file_content.encode('utf-8')
            else:
                content = self.voter_file_content

            # now we have to handle non-universal-newline stuff
            # we do this in a simple way: replace all \r with \n
            # then, replace all double \n with single \n
            # this should leave us with only \n
            content = content.replace('\r', '\n').replace('\n\n', '\n')

            voter_stream = io.BytesIO(content)
        else:
            voter_stream = open(self.voter_file.path, "rU")

        #reader = unicode_csv_reader(voter_stream)
        reader = unicodecsv.reader(voter_stream, encoding='utf-8')

        for voter_fields in reader:
            # bad line
            if len(voter_fields) < 1:
                continue

            return_dict = {'voter_id': voter_fields[0].strip()}

            if len(voter_fields) > 1:
                if validate_email(voter_fields[1].strip()):
                    return_dict['email'] = voter_fields[1].strip()
                else:
                    return_dict['name'] = voter_fields[1].strip()
            else:
                # assume single field means the email is the same field
                return_dict['email'] = voter_fields[0].strip()

            if len(voter_fields) > 2:
                if validate_email(voter_fields[1].strip()):
                    return_dict['name'] = voter_fields[2].strip()
                else:
                    return_dict['user_type'] = voter_fields[2].strip()
            else:
                return_dict['name'] = return_dict['email']

            if len(voter_fields) > 3:
                return_dict['user_type'] = voter_fields[3].strip()

            yield return_dict

    def process(self):
        self.processing_started_at = datetime.datetime.utcnow()
        self.save()

        election = self.election
        last_alias_num = election.last_alias_num

        num_voters = 0
        new_voters = []
        for voter in self.itervoters():
            # does voter for this user already exist
            existing_voter = Voter.get_by_election_and_voter_id(election, voter['voter_id'])

            # create the voter
            if not existing_voter:
                num_voters += 1

                user = None
                if 'user_type' in voter.keys():
                    if 'email' in voter.keys():
                        user = User.update_or_create(voter['user_type'], voter['voter_id'], voter['name'], {'email': voter['email']})
                    else:
                        user = User.update_or_create(voter['user_type'], voter['voter_id'], voter['name'], {})

                voter_uuid = str(uuid.uuid4())
                if 'email' in voter.keys():
                    new_voter = Voter(uuid=voter_uuid, user=user, voter_name=voter['name'], voter_email=voter['email'], election=election)
                else:
                    new_voter = Voter(uuid=voter_uuid, user=user, voter_name=voter['name'], election=election)

                new_voter.voter_login_id = voter['voter_id']

                if not user:
                    new_voter.generate_password()

                new_voters.append(new_voter)
                new_voter.save()

        if election.use_voter_aliases:
            voter_alias_integers = range(last_alias_num + 1, last_alias_num + 1 + num_voters)
            random.shuffle(voter_alias_integers)
            for i, new_voter in enumerate(new_voters):
                new_voter.alias = 'V%s' % voter_alias_integers[i]
                new_voter.save()

        self.num_voters = num_voters
        self.processing_finished_at = datetime.datetime.utcnow()
        self.save()

        return num_voters


class Voter(HeliosModel):
    election = models.ForeignKey(Election)

    uuid = models.CharField(max_length=50)

    # for users of type password, no user object is created
    # but a dynamic user object is created automatically
    user = models.ForeignKey('helios_auth.User', null=True)

    # if user is null, then you need a voter login ID and password
    voter_login_id = models.CharField(max_length=100, null=True)
    voter_password = models.CharField(max_length=100, null=True)
    voter_name = models.CharField(max_length=200, null=True)
    voter_email = models.CharField(max_length=250, null=True)

    # if election uses aliases
    alias = models.CharField(max_length=100, null=True)

    # we keep a copy here for easy tallying
    vote = LDObjectField(type_hint='legacy/EncryptedVote', null=True)
    vote_hash = models.CharField(max_length=100, null=True)
    cast_at = models.DateTimeField(auto_now_add=False, null=True)

    class Meta:
        unique_together = (('election', 'voter_login_id'))

    def __init__(self, *args, **kwargs):
        super(Voter, self).__init__(*args, **kwargs)

        # stub the user so code is not full of IF statements
        if not self.user:
            self.user = User(user_type='password', user_id=self.voter_email, name=self.voter_name)

    @classmethod
    @transaction.commit_on_success
    def register_user_in_election(cls, user, election):
        voter_uuid = str(uuid.uuid4())
        voter = Voter(uuid=voter_uuid, user=user, election=election)

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
        query = cls.objects.filter(election=election)

        # the boolean check is not stupid, this is ternary logic
        # none means don't care if it's cast or not
        if cast == True:
            query = query.exclude(cast_at=None)
        elif cast == False:
            query = query.filter(cast_at=None)

        # little trick to get around GAE limitation
        # order by uuid only when no inequality has been added
        if cast == None or order_by == 'cast_at' or order_by == '-cast_at':
            query = query.order_by(order_by)

            # if we want the list after a certain UUID, add the inequality here
            if after:
                if order_by[0] == '-':
                    field_name = "%s__gt" % order_by[1:]
                else:
                    field_name = "%s__gt" % order_by
                conditions = {field_name: after}
                query = query.filter(**conditions)

        if limit:
            query = query[:limit]

        return query

    @classmethod
    def get_all_by_election_in_chunks(cls, election, cast=None, chunk=100):
        return cls.get_by_election(election)

    @classmethod
    def get_by_election_and_voter_id(cls, election, voter_id):
        try:
            return cls.objects.get(election=election, voter_login_id=voter_id)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_by_election_and_user(cls, election, user):
        try:
            return cls.objects.get(election=election, user=user)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_by_election_and_uuid(cls, election, uuid):
        query = cls.objects.filter(election=election, uuid=uuid)

        try:
            return query[0]
        except:
            return None

    @classmethod
    def get_by_user(cls, user):
        return cls.objects.select_related().filter(user=user).order_by('-cast_at')

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

        return CastVote.objects.get(vote_hash=self.vote_hash).vote_tinyhash

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
        if self.voter_email:
            send_mail(subject, body, settings.SERVER_EMAIL, ["%s <%s>" % (self.name, self.voter_email)], fail_silently=False)
        else:
            self.user.send_message(subject, body)

    def generate_password(self, length=10):
        if self.voter_password:
            raise Exception("Password already exists")

        self.voter_password = heliosutils.random_string(length, alphabet='abcdefghijkmnopqrstuvwxyzABCDEFGHIJKLMNPQRSTUVWXYZ23456789')

    def store_vote(self, cast_vote):
        # only store the vote if it's cast later than the current one
        if self.cast_at and cast_vote.cast_at < self.cast_at:
            return

        self.vote = cast_vote.vote
        self.vote_hash = cast_vote.vote_hash
        self.cast_at = cast_vote.cast_at
        self.save()

    def last_cast_vote(self):
        return CastVote(vote=self.vote, vote_hash=self.vote_hash, cast_at=self.cast_at, voter=self)


class CastVote(HeliosModel):
    # the reference to the voter provides the voter_uuid
    voter = models.ForeignKey(Voter)

    # the actual encrypted vote
    vote = LDObjectField(type_hint='legacy/EncryptedVote')

    # cache the hash of the vote
    vote_hash = models.CharField(max_length=100, unique=True)

    # a tiny version of the hash to enable short URLs
    vote_tinyhash = models.CharField(max_length=50, null=True, unique=True)

    cast_at = models.DateTimeField(auto_now_add=True)

    # some ballots can be quarantined (this is not the same thing as
    # provisional)
    quarantined_p = models.BooleanField(default=False, null=False)
    released_from_quarantine_at = models.DateTimeField(auto_now_add=False, null=True)

    # when is the vote verified?
    verified_at = models.DateTimeField(null=True)
    invalidated_at = models.DateTimeField(null=True)

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
            safe_hash = safe_hash.replace(c, '')

        length = 8
        while True:
            vote_tinyhash = safe_hash[:length]
            if CastVote.objects.filter(vote_tinyhash=vote_tinyhash).count() == 0:
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
        return cls.objects.filter(voter=voter).order_by('-cast_at')

    def verify_and_store(self):
        # if it's quarantined, don't let this go through
        if self.is_quarantined:
            raise Exception("Cast vote is quarantined, verification and storage is delayed.")

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
            issues.append("The vote's election UUID does not match the election for which this vote is being cast.")

        return issues


class AuditedBallot(models.Model):

    """
    ballots for auditing
    """
    election = models.ForeignKey(Election)
    raw_vote = models.TextField()
    vote_hash = models.CharField(max_length=100)
    added_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def get(cls, election, vote_hash):
        return cls.objects.get(election=election, vote_hash=vote_hash)

    @classmethod
    def get_by_election(cls, election, after=None, limit=None):
        query = cls.objects.filter(election=election).order_by('vote_hash')

        # if we want the list after a certain UUID, add the inequality here
        if after:
            query = query.filter(vote_hash__gt=after)

        if limit:
            query = query[:limit]

        return query


class Key(models.Model):
    name = models.CharField(max_length=40)
    email = models.CharField(max_length=60)
    public_key_encrypt = models.CharField(max_length=10000)
    public_key_signing = models.CharField(max_length=10000)
    pok_encrypt = models.CharField(max_length=10000)
    pok_signing = models.CharField(max_length=10000)
    public_key_encrypt_hash = models.CharField(max_length=100)
    public_key_signing_hash = models.CharField(max_length=100)


class SecretKey(models.Model):
    public_key = models.ForeignKey(Key)
    secret_key_encrypt = models.CharField(max_length=10000, null=True)
    secret_key_signing = models.CharField(max_length=10000, null=True)


class SignedEncryptedShare(models.Model):
    election_id = models.IntegerField()
    share = models.CharField(max_length=10000000)
    signer = models.CharField(max_length=40)
    signer_id = models.IntegerField()
    receiver = models.CharField(max_length=40)
    receiver_id = models.IntegerField()
    trustee_signer_id = models.IntegerField()
    trustee_receiver_id = models.IntegerField()


class Signature(models.Model):
    signature = models.CharField(max_length=10000)


class Ei(models.Model):
    election_id = models.IntegerField()
    value = models.CharField(max_length=10000)
    signer_id = models.IntegerField()
    signer = models.CharField(max_length=40)


class IncorrectShare(models.Model):
    share = models.CharField(max_length=100000)
    election_id = models.IntegerField()
    sig = models.CharField(max_length=100000)
    signer_id = models.IntegerField()
    receiver_id = models.IntegerField()
    explanation = models.CharField(max_length=200)


class Trustee(HeliosModel):
    election = models.ForeignKey(Election)

    uuid = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    secret = models.CharField(max_length=100)

    # public key
    public_key = LDObjectField(type_hint='legacy/EGPublicKey', null=True)
    public_key_hash = models.CharField(max_length=100)

    # secret key
    # if the secret key is present, this means
    # Helios is playing the role of the trustee.
    secret_key = LDObjectField(type_hint='legacy/EGSecretKey', null=True)

    # proof of knowledge of secret key
    pok = LDObjectField(type_hint='legacy/DLogProof', null=True)

    # decryption factors
    decryption_factors = LDObjectField(type_hint=datatypes.arrayOf(datatypes.arrayOf('core/BigInteger')), null=True)

    decryption_proofs = LDObjectField(type_hint=datatypes.arrayOf(datatypes.arrayOf('legacy/EGZKProof')), null=True)
    key = models.ForeignKey(Key, null=True)
    helios_trustee = models.BooleanField(default=False, null=False)
    added_encrypted_shares = models.BooleanField(default=False, null=False)

    class Meta:
        unique_together = (('election', 'email'))

    def save(self, *args, **kwargs):
        """
        override this just to get a hook
        """
        # not saved yet?
        if not self.secret:
            self.secret = heliosutils.random_string(12)
            self.election.append_log("Trustee %s added" % self.name)

        super(Trustee, self).save(*args, **kwargs)

    @classmethod
    def get_by_election(cls, election):
        return cls.objects.filter(election=election).order_by('id')

    @classmethod
    def get_by_pointnumber(cls, point_number):
        if len(cls.objects.filter(point_number=point_number)) > 0:
            return cls.objects.filter(point_number=point_number)[0]

    @classmethod
    def get_by_uuid(cls, uuid):
        return cls.objects.get(uuid=uuid)

    @classmethod
    def get_by_election_and_uuid(cls, election, uuid):
        return cls.objects.get(election=election, uuid=uuid)

    @classmethod
    def get_by_election_and_email(cls, election, email):
        try:
            return cls.objects.get(election=election, email=email)
        except cls.DoesNotExist:
            return None

    @property
    def datatype(self):
        return self.election.datatype.replace('Election', 'Trustee')

    def send_message(self, subject, body):
        send_mail(subject, body, settings.SERVER_EMAIL, ["%s <%s>" % (self.name, self.email)], fail_silently=False)

    def verify_decryption_proofs(self):
        """
        verify that the decryption proofs match the tally for the election
        """
        return self.election.encrypted_tally.verify_decryption_proofs(self.decryption_factors, self.decryption_proofs, self.public_key, algs.EG_fiatshamir_challenge_generator)

    def prepare_mpc(self, scheme):
        trustees = self.election.get_trustees()
        n = len(trustees)
        q = self.public_key.q
        s = self.secret_key.x
        scheme.share_verifiably(self, s)

        self.prepared_mpc = True
        # self.save()

    def check_if_prepared_mpc(self):
        if self.prepared_mpc == True:
            return True
        else:
            return False

    def add_encrypted_shares(self, election):
        trustees = Trustee.objects.filter(election=election).order_by('id')
        scheme = ThresholdScheme.objects.get(election=election)

        n = scheme.n

        key_list = []
        for i in range(len(trustees)):
            key_list.append(trustees[i].key)

        if not self.key in key_list:
            return Exception('The trustee does not belong to the given election')

        secret_key = SecretKey.objects.get(public_key=self.key)
        secret_key_signing = algs.EGSecretKey.from_dict(utils.from_json(secret_key.secret_key_signing))

        if (len(SignedEncryptedShare.objects.filter(signer_id=self.key.id).filter(election_id=election.id)) > 0):
            return Exception("The trustee's shares were already uploaded")

        s = algs.Utils.random_mpz_lt(q)
        t = algs.Utils.random_mpz_lt(q)

        shares = scheme.share_verifiably(s, t, ELGAMAL_PARAMS)

        if len(key_list) == len(shares):
            for i in range(len(trustees)):
                trustee = trustees[i]

                key = trustee.key
                receiver = key.name
                receiver_id = key.id

                share = shares[i]
                share_string = utils.to_json_js(share.to_dict())
                if share.point_s.x_value != trustee.id:
                    return Exception('Shares have wrong x_coordinate')

                encrypted_share = share.encrypt(algs.EGPublicKey.from_dict(utils.from_json(key.public_key_encrypt)))
                signature = share.sign(secret_key_signing, p, q, g)
                signed_encrypted_share = thresholdalgs.SignedEncryptedShare(signature, encrypted_share)

                encrypted_share = SignedEncryptedShare()
                encrypted_share.share = utils.to_json(signed_encrypted_share.to_dict())
                if signature.verify(share_string, algs.EGPublicKey.from_dict(utils.from_json(self.key.public_key_signing)), p, q, g):
                    encrypted_share.signer = self.key.name
                    encrypted_share.signer_id = self.key.id
                    encrypted_share.receiver = receiver
                    encrypted_share.receiver_id = receiver_id
                    encrypted_share.election_id = election.id
                    encrypted_share.trustee_receiver_id = trustee.id
                    encrypted_share.trustee_signer_id = self.id
                    encrypted_share.save()

                else:
                    return Exception('Wrong signature')

            self.added_encrypted_shares = True

        else:
            return Exception('Different number of keys and shares')

    def calculate_key(self, election):
        secret_key_string = SecretKey.objects.get(public_key=self.key).secret_key_encrypt
        secret_key = elgamal.SecretKey.from_dict(utils.from_json(secret_key_string))
        receiver_id = self.key.id
        scheme = ThresholdScheme.objects.get(election=election)
        n = scheme.n
        k = scheme.k

        # write data_receiver
        signed_encrypted_shares_strings = SignedEncryptedShare.objects.filter(receiver_id=receiver_id).filter(election_id=election.id).order_by('signer_id')
        signed_encrypted_shares = []
        receiver_ids = []
        signer_ids = []

        for share in signed_encrypted_shares_strings:
            signed_encrypted_shares.append(thresholdalgs.SignedEncryptedShare.from_dict(utils.from_json(share.share)))
            receiver_ids.append(share.receiver_id)
            signer_ids.append(share.signer_id)

        correct_secret_shares = []
        if len(signed_encrypted_shares) == n:
            for j in range(len(signed_encrypted_shares)):
                element = signed_encrypted_shares[j]
                receiver_id_share = receiver_ids[j]
                signer_id_share = signer_ids[j]
                pk_signer_signing = elgamal.PublicKey.from_dict(utils.from_json(Key.objects.get(id=signer_id_share).public_key_signing))

                encry_share = element.encr_share
                sig = element.sig
                share = encry_share.decrypt(secret_key)
                share_string = utils.to_json_js(share.to_dict())

                correct_share = False
                if sig.verify(share_string, pk_signer_signing, p, q, g):
                    if share.verify_share(scheme, p, q, g):
                        correct_secret_shares.append(share)
                        correct_share = True
                    else:
                        share_string = utils.to_json(share.to_dict())
                        IncorrectShare = IncorrectShare(share_string, election.id, sig, signer_id, receiver_id, 'invalid commitments')
                        IncorrectShare.save()
                else:
                    share_string = utils.to_json(share.to_dict())
                    incorrect_share = IncorrectShare()
                    incorrect_share.share = share_string
                    incorrect_share.election_id = election.id
                    incorrect_share.sig = sig

                    incorrect_share.signer_id = signer_id_share
                    incorrect_share.receiver_id = receiver_id_share
                    incorrect_share.explanation = 'invalid signature'
                    incorrect_share.save()

        if len(correct_secret_shares) == n:
            share = correct_secret_shares[0]
            for i in range(1, len(correct_secret_shares)):
                share.add(correct_secret_shares[i], p, q, g)

            if share.verify_share(scheme, p, q, g):
                final_public_key = elgamal.PublicKey()
                final_public_key.q = q
                final_public_key.g = g
                final_public_key.p = p
                final_public_key.y = pow(g, share.point_s.y_value, p)
                final_secret_key = elgamal.SecretKey()
                final_secret_key.public_key = final_public_key
                final_secret_key.x = share.point_s.y_value

                self.public_key = final_public_key
                self.secret_key = final_secret_key
                self.public_key_hash = datatypes.LDObject.instantiate(self.public_key, datatype='legacy/EGPublicKey').hash
                self.pok = self.secret_key.prove_sk(algs.DLog_challenge_generator)


class ThresholdScheme(HeliosModel):
    election = models.ForeignKey(Election)
    n = models.IntegerField(null=True)
    k = models.IntegerField(null=True)
    ground_1 = LDObjectField(type_hint='core/BigInteger', null=True)
    ground_2 = LDObjectField(type_hint='core/BigInteger', null=True)

    def save(self, *args, **kwargs):
        # not saved yet?
        if not self.election:
            self.election.append_log('ThresholdScheme for %s added' % election.name)

        super(ThresholdScheme, self).save(*args, **kwargs)

    # share a secret verifiably by creating a polynomial of grade k-1 and generate n points
    # the secret s is F(0) and can be found by interpolating the points
    #
    # commitments E contain commitments to the point
    # commitments Ei contain commitments to the coefficients of the polynomial
    def share_verifiably(self, s, t, EG):
        election = self.election
        trustees = Trustee.objects.filter(election=election).order_by('id')

        F = thresholdalgs.Polynomial(s, self, EG)
        G = thresholdalgs.Polynomial(t, self, EG)

        # create points on polynomials from x values from 0 to n, where F(O) is the secret
        points_F = F.create_points(trustees)
        points_G = G.create_points(trustees)

        # create commitments
        Ei = []
        for i in range(self.k):
            commitment_loop = thresholdalgs.CommitmentE()
            commitment_loop.generate(F.coeff[i], G.coeff[i], self.ground_1, self.ground_2, p, q, g)
            if commitment_loop.value > p - 1:
                raise Exception('Ei value too big!')
            Ei.append(commitment_loop)

        shares = []
        for i in range(self.n):
            share = thresholdalgs.Share(points_F[i], points_G[i], Ei)
            if share.verify_share(self, p, q, g):
                shares.append(share)
            else:
                return None

        return shares

    @classmethod
    def get_by_election(cls, election):
        return cls.objects.filter(election=election)

    @property
    def datatype(self):
        return self.election.datatype.replace('Election', 'ThresholdScheme')
