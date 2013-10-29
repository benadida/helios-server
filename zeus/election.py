# -*- coding: utf-8 -*-
import datetime
import uuid
import json
import copy
import re

from django.utils.datastructures import SortedDict
from django.utils.translation import ugettext_lazy as _

from zeus.core import ZeusCoreElection, Teller, sk_from_args, \
    mix_ciphers, TellerStream, gamma_count_parties, gamma_count_range
from zeus.core import V_CAST_VOTE, V_PUBLIC_AUDIT, V_AUDIT_REQUEST, \
    gamma_decode, to_absolute_answers, ZeusError

from django.conf import settings

from helios.crypto import electionalgs
from helios.crypto import utils
from helios import models as helios_models
from helios.views import ELGAMAL_PARAMS
from helios import datatypes
from stv.stv import count_stv, Ballot

from django.db import connection
from hashlib import sha256


MIXNET_NR_PARALLEL = getattr(settings, 'ZEUS_MIXNET_NR_PARALLEL', 2)
MIXNET_NR_ROUNDS = getattr(settings, 'ZEUS_MIXNET_NR_ROUNDS', 128)


class NullStream(object):
    """
    Dummy stream
    """
    def read(*args):
        return ''

    def write(*args):
        return


def get_datatype(datatype, obj=None, **kwargs):
    if len(datatype.split("/")) == 1:
        datatype = 'legacy/%s' % datatype

    obj = obj or kwargs
    return datatypes.LDObject.fromDict(obj, type_hint=datatype)


class ZeusDjangoElection(ZeusCoreElection):
    """
    Implement required core do_store/do_get methods.
    """
    @classmethod
    def from_election(self, election):
        return ZeusDjangoElection(election=election, poll=None)

    @classmethod
    def from_poll(self, poll):
        return ZeusDjangoElection(election=poll.election, poll=poll)

    def __init__(self, election=None, poll=None, *args, **kwargs):

        if poll and not election:
            election = poll.election

        self.election = election
        self.poll = poll

        kwargs['cryptosystem'] = (ELGAMAL_PARAMS.p, ELGAMAL_PARAMS.g,
                                  ELGAMAL_PARAMS.q)
        kwargs['teller'] = Teller(outstream=NullStream())
        super(ZeusDjangoElection, self).__init__(*args, **kwargs)
        self.set_option(parallel=MIXNET_NR_PARALLEL)
        self.set_option(nr_parallel=MIXNET_NR_PARALLEL)
        self.set_option(min_mix_rounds=MIXNET_NR_ROUNDS)

    def _get_zeus_vote(self, enc_vote, voter=None, audit_password=None):
        return self.poll._get_zeus_vote(enc_vote, voter=voter,
                                                  audit_password=audit_password)

    def do_get_vote(self, fingerprint):
        # try CastVote
        try:
            vote = self.poll.cast_votes.get(fingerprint=fingerprint)
            zeus_vote = self._get_zeus_vote(vote.vote)
            zeus_vote['fingerprint'] = vote.fingerprint
            zeus_vote['signature'] = vote.signature['signature']
            zeus_vote['previous'] = vote.previous
            zeus_vote['voter'] = vote.voter.uuid
            zeus_vote['index'] = vote.index
            zeus_vote['weight'] = vote.voter.voter_weight
            return zeus_vote
        except helios_models.CastVote.DoesNotExist:
            pass
        # then AuditedBallot
        try:
            audited = self.poll.audited_ballots.get(
                fingerprint=fingerprint, is_request=False)
            helios_vote = electionalgs.EncryptedVote.fromJSONDict(
                utils.from_json(audited.raw_vote))
            zeus_vote = self._get_zeus_vote(
                helios_vote,
                audit_password=audited.audit_code)
            zeus_vote['fingerprint'] = audited.fingerprint
            zeus_vote['signature'] = audited.signature['signature']
            return zeus_vote
        except helios_models.AuditedBallot.DoesNotExist:
            pass
        # then AuditedBallot requests
        try:
            audited = self.poll.audited_ballots.get(
                fingerprint=fingerprint, is_request=True)
            helios_vote = electionalgs.EncryptedVote.fromJSONDict(
                utils.from_json(audited.raw_vote))
            zeus_vote = self._get_zeus_vote(
                helios_vote,
                audit_password=audited.audit_code)
            zeus_vote['fingerprint'] = audited.fingerprint
            zeus_vote['signature'] = audited.signature['signature']
            return zeus_vote
        except helios_models.AuditedBallot.DoesNotExist:
            return None
        return None

    def do_get_cast_votes(self, voter):
        votes = []
        for vote in self.poll.cast_votes.filter(verified_at__isnull=False,
                                                           voter__uuid=voter).order_by('pk'):
            votes.append(vote.fingerprint)
        return votes

    def do_get_all_cast_votes(self):
        votes = {}
        for voter in self.do_get_voters():
            voter_votes = [vote for vote in self.do_get_cast_votes(voter)]
            if voter_votes:
                votes[voter] = voter_votes
        return votes

    def do_index_vote(self, fingerprint):
        # TODO: READ FOR UPDATE
        index = self.poll.cast_votes.filter(verified_at__isnull=False).count()
        return index

    def do_get_index_vote(self, index):
        return self.poll.cast_votes.get(index=index).fingerprint

    def do_get_vote_index(self):
        votes = []
        for vote in self.poll.cast_votes.filter(index__isnull=False).order_by('index'):
            votes.append(vote.fingerprint)
        return votes

    def do_get_votes(self):
        votes = {}
        casted = self._casted_votes()
        audited = self._audit_votes()
        votes.update(casted)
        votes.update(audited)
        return votes

    def _audit_votes(self):
        votes = {}
        for audited in self.poll.audited_ballots.filter(is_request=False):
            helios_vote = electionalgs.EncryptedVote.fromJSONDict(
                utils.from_json(audited.raw_vote))
            zeus_vote = self._get_zeus_vote(
                helios_vote,
                audit_password=audited.audit_code)
            zeus_vote['fingerprint'] = audited.fingerprint
            zeus_vote['signature'] = audited.signature['signature']
            votes[audited.fingerprint] = zeus_vote
        for audited in self.poll.audited_ballots.filter(is_request=True):
            try:
                self.poll.audited_ballots.get(fingerprint=audited.fingerprint,
                                                        is_request=False)
            except helios_models.AuditedBallot.DoesNotExist:
                helios_vote = electionalgs.EncryptedVote.fromJSONDict(
                    utils.from_json(audited.raw_vote))
                zeus_vote = self._get_zeus_vote(
                    helios_vote,
                    audit_password=audited.audit_code)
                zeus_vote['fingerprint'] = audited.fingerprint
                zeus_vote['signature'] = audited.signature['signature']
                votes[audited.fingerprint] = zeus_vote

        return votes

    def _casted_votes(self):
        votes = {}
        for vote in self.poll.cast_votes.filter(verified_at__isnull=False):
            zeus_vote = self._get_zeus_vote(vote.vote, voter=vote.voter)
            zeus_vote['fingerprint'] = vote.fingerprint
            zeus_vote['signature'] = vote.signature['signature']
            zeus_vote['previous'] = vote.previous
            zeus_vote['voter'] = vote.voter.uuid
            zeus_vote['index'] = vote.index
            votes[vote.fingerprint] = zeus_vote
        return votes

    def do_store_audit_publication(self, fingerprint):
        pass

    def do_store_audit_request(self, fingerprint, voter):
        pass

    def do_get_audit_requests(self):
        reqs = {}
        for req in self.poll.audited_ballots.filter(is_request=True):
            reqs[req.fingerprint] = req.voter.uuid
        return reqs

    def do_get_audit_request(self, fingerprint):
        try:
            obj = self.poll.audited_ballots.get(
                fingerprint=fingerprint,
                is_request=True)
        except helios_models.AuditedBallot.DoesNotExist:
            return None
        return obj.voter.uuid

    def do_get_audit_publications(self):
        pubs = []
        for pub in self.poll.audited_ballots.filter(is_request=False):
            pubs.append(pub.fingerprint)

        return pubs

    def _get_helios_vote_dict(self, vote):
        enc_ballot = vote['encrypted_ballot']
        ballot = {
            'election_hash': '',
            'election_uuid': self.poll.uuid,
            'answers': [{
                'encryption_proof': [enc_ballot['commitment'], enc_ballot['challenge'],
                                     enc_ballot['response']],
                'choices':[{'alpha': enc_ballot['alpha'], 'beta': enc_ballot['beta']}]
            }]
        }
        return ballot

    def _do_store_cast_vote(self, vote):
        helios_vote = self._get_helios_vote_dict(vote)
        enc_vote = get_datatype('phoebus/EncryptedVote', helios_vote)
        vote_hash = electionalgs.EncryptedVote.fromJSONDict(enc_vote.toJSONDict()).get_hash()
        vobj = helios_models.CastVote(vote=enc_vote)
        vobj.voter = self._get_voter_object(vote['voter'])
        vobj.poll = self.poll
        vobj.vote_hash = vote_hash
        vobj.cast_at = datetime.datetime.now()
        vobj.verified_at = datetime.datetime.now()
        vobj.fingerprint = vote['fingerprint']
        vobj.signature = {'signature': vote['signature']}
        vobj.index = vote['index']
        if 'audit_code' in vote:
            vobj.audit_code = vote['audit_code']
        if vote['previous']:
            vobj.previous = vote['previous']
        vobj.save()

        voter = self._get_voter_object(vote['voter'])
        voter.vote = enc_vote
        voter.vote_fingerprint = vobj.fingerprint
        voter.vote_signature = vobj.signature
        voter.vote_hash = vobj.vote_hash
        voter.vote_index = vote['index']
        voter.cast_at = vobj.cast_at
        voter.save()

    def _do_store_audit_request(self, vote):
        helios_vote = self._get_helios_vote_dict(vote)
        enc_vote = get_datatype('phoebus/EncryptedVote', helios_vote)
        enc_vote = electionalgs.EncryptedVote.fromJSONDict(enc_vote.toJSONDict())
        vobj = helios_models.AuditedBallot()
        vobj.raw_vote = enc_vote.toJSON()
        vobj.poll = self.poll
        vobj.vote_hash = enc_vote.get_hash()
        vobj.fingerprint = vote['fingerprint']
        vobj.is_request = True
        vobj.audit_code = vote['audit_code']
        vobj.signature = {'signature': vote['signature']}
        vobj.voter = self._get_voter_object(vote['voter'])

        vobj.save()

    def _do_store_public_audit(self, vote):
        vobj = helios_models.AuditedBallot.objects.get(poll=self.poll,
                                                       fingerprint=vote['fingerprint'],
                                                       is_request=True)

        vobj.pk = None
        vobj.signature = {'signature': vote['signature']}
        vobj.fingerprint = vote['fingerprint']
        new_vote = vobj.vote
        new_vote.encrypted_answers[0].randomness = [vote['voter_secret']]
        new_vote.encrypted_answers[0].answer = vote['plaintext']
        vobj.raw_vote = json.dumps(new_vote.toJSONDict(with_randomness=True))
        vobj.is_request = False
        vobj.save()

    def do_store_votes(self, votes):
        for vote in votes:
            if vote['status'] == V_CAST_VOTE:
                self._do_store_cast_vote(vote)
            if vote['status'] == V_AUDIT_REQUEST:
                self._do_store_audit_request(vote)
            if vote['status'] == V_PUBLIC_AUDIT:
                self._do_store_public_audit(vote)

    def do_get_candidates(self):
        try:
            candidates = self.poll.questions[0]['answers']
        except IndexError:
            candidates = []
        return candidates

    def _get_voter_object(self, voter_uuid):
        return self.poll.voters.get(uuid=voter_uuid)

    def do_get_voter(self, voter_uuid):
        v = self._get_voter_object(voter_uuid)
        return v.zeus_string, v.voter_weight

    def do_get_voters(self):
        voters = {}
        for v in self.poll.voters.all():
            voters[v.uuid] = v.zeus_string, v.voter_weight

        return voters

    def do_store_election_public(self, public):
        p, g, q = self.do_get_cryptosystem()
        pk = get_datatype('EGPublicKey', p=p, g=g, q=q, y=public).wrapped_obj
        election = self.election
        election.public_key = pk
        election.save()

    def do_get_election_public(self):
        if self.election.public_key:
            return self.election.public_key.y
        return None

    def do_get_voter_audit_codes(self, voter):
        return self.poll.voters.get(
            uuid=voter).get_audit_passwords()

    def do_get_all_voter_audit_codes(self):
        voter_slots = {}
        for v in self.poll.voters.all():
            voter_slots[v.uuid] = v.get_audit_passwords()

        return voter_slots

    def do_get_cryptosystem(self):
        return [ELGAMAL_PARAMS.p, ELGAMAL_PARAMS.g,
                                  ELGAMAL_PARAMS.q]

    def do_store_zeus_key(self, secret, public,
                                commitment, challenge, response):

        p, g, q = self.do_get_cryptosystem()
        pk = get_datatype('EGPublicKey', p=p, g=g, q=q, y=public)
        trustee, created = helios_models.Trustee.objects.get_or_create(
            election=self.election,
            public_key_hash=pk.hash)

        trustee.uuid = str(uuid.uuid4())
        trustee.name = settings.DEFAULT_FROM_NAME
        trustee.email = settings.DEFAULT_FROM_EMAIL

        p, g, q = self.do_get_cryptosystem()
        pk = get_datatype('EGPublicKey', p=p, g=g, q=q, y=public)
        trustee.public_key = pk

        sk = get_datatype('EGSecretKey', public_key=pk.toDict(), x=secret)
        trustee.secret_key = sk
        trustee.last_verified_key_at = datetime.datetime.now()
        trustee.public_key_hash = pk.hash

        pok = get_datatype('DLogProof', commitment=commitment,
                           challenge=challenge, response=response)
        trustee.pok = pok
        trustee.save()

    def _get_zeus_trustee(self):
        return self.election.get_zeus_trustee()

    def do_get_zeus_key(self):
        t = self._get_zeus_trustee()
        args = self.do_get_cryptosystem()
        args += [t.secret_key.x, t.public_key.y]
        args += (t.pok.commitment, t.pok.challenge, t.pok.response)
        return sk_from_args(*args)

    def do_get_zeus_secret(self):
        trustee = self._get_zeus_trustee()
        return trustee.secret_key.x if trustee else None

    def do_get_zeus_public(self):
        trustee = self._get_zeus_trustee()
        return trustee.public_key.y if trustee else None

    def do_get_zeus_key_proof(self):
        trustee = self._get_zeus_trustee()
        if not trustee:
            return None
        pok = trustee.pok
        return [pok.commitment, pok.challenge, pok.response]

    def do_store_trustee_factors(self, factors):
        pass

    def do_store_trustee(self, public, commitment, challenge, response):
        p, g, q = self.do_get_cryptosystem()
        pk = get_datatype('EGPublicKey', p=p, g=g, q=q, y=public)
        t, created = helios_models.Trustee.objects.get_or_create(
            public_key_hash=pk.hash, election=self.election)
        if created:
            t.name = "trustee"
            t.email = "trustee@test.com"

        if not t.public_key:
            t.public_key = get_datatype('EGPublicKey', p=p, g=g, q=q, y=public)

        if not t.pok:
            t.public_key = get_datatype('DLogProof', p=p, g=g, q=q, y=public)

        t.public_key.y = public
        t.pok.commitment = commitment
        t.pok.challenge = challenge
        t.pok.response = response
        t.save()

    def do_get_trustee(self, public):
        p, g, q = self.do_get_cryptosystem()
        pk = get_datatype('EGPublicKey', p=p, g=g, q=q, y=public)
        t = helios_models.Trustee.objects.get(public_key_hash=pk.hash,
                                              election=self.election)
        return [t.pok.commitment, t.pok.challenge, t.pok.response]

    def do_get_trustees(self):
        trustees = self.election.trustees.filter(
            secret_key__isnull=True, public_key__isnull=False)
        zeus_trustees = {}

        for t in trustees:
          public = t.public_key.y
          zeus_trustees[public] = [t.pok.commitment, t.pok.challenge,
                                   t.pok.response]
        return zeus_trustees

    def do_get_all_trustee_factors(self):
        factors = {}
        for trustee in self.election.trustees.filter(
            secret_key__isnull=True):
          factors[trustee.public_key.y] = self._get_zeus_factors(trustee)
        return factors

    def do_get_last_mix(self):
        mixnet = helios_models.PollMix.objects.filter(
            poll=self.poll,
            status='finished').order_by('-mix_order')
        if mixnet.count() == 0:
            return self.extract_votes_for_mixing()[0]
        return mixnet[0].zeus_mix()

    def do_store_mix(self, mix):
      pass

    def do_get_all_mixes(self):
        mixes = [self.extract_votes_for_mixing()[0]]
        for mixnet in self.poll.mixes.filter(status='finished').order_by('mix_order'):
          mixes.append(mixnet.zeus_mix())
        return mixes

    def mix(self, ciphers):
      return mix_ciphers(ciphers, teller=self.teller,
                            nr_rounds=MIXNET_NR_ROUNDS,
                           nr_parallel=self.get_option('parallel'))

    def _get_zeus_factors(self, trustee):
        trustee_factors = []
        factors = trustee.partial_decryptions.get(poll=self.poll)
        for index, factor in enumerate(factors.decryption_factors[0]):
            zeus_factor = []
            proof = factors.decryption_proofs[0][index]
            zeus_factor.append(factor)
            proof = [proof.commitment['A'],
                     proof.commitment['B'],
                     proof.challenge,
                     proof.response]
            zeus_factor.append(proof)
            trustee_factors.append(zeus_factor)
        return trustee_factors

    def do_get_zeus_factors(self):
        trustee = self._get_zeus_trustee()
        return self._get_zeus_factors(trustee)

    def do_store_zeus_factors(self, factors):
        t = self._get_zeus_trustee()
        helios_factors = [[]]
        helios_proofs = [[]]

        for factor in factors:
            proof_obj = get_datatype('EGZKProof',{
                'commitment': {
                    'A':factor[1][0],
                    'B': factor[1][1]},
                'challenge': factor[1][2],
                'response': factor[1][3]
            })
            helios_factors[0].append(factor[0])
            helios_proofs[0].append(proof_obj)

        factors = t.partial_decryptions.create(poll=self.poll)
        factors.decryption_factors = helios_factors
        factors.decryption_proofs = helios_proofs
        factors.save()

    def do_store_results(self, results):
        e = self.poll
        e.result = [results]
        e.save()

    def do_get_results(self):
        return self.poll.result[0]

    @classmethod
    def mk_random(cls, *args, **kwargs):
        helios_models.Election.objects.create(uuid=kwargs.get('uuid'))
        super(cls, ZeusDjangoElection).mk_random(*args, **kwargs)

    def do_store_excluded_voter(self, voter_key, reason):
        voter = self.poll.voters.get(uuid=voter_key)
        voter.excluded_at = datetime.datetime.now()
        voter.exclude_reason = reason
        voter.save()

    def do_get_excluded_voters(self):
        excluded_voters = {}
        for voter in self.poll.voters.filter(
                excluded_at__isnull=False):
            excluded_voters[voter.uuid] = voter.exclude_reason
        return excluded_voters

    def get_results(self):
        if self.poll.get_module().module_id == 'score':
            # last entry should be question min/max params
            # catch untagged entries for backwards compatibility
            candidates = self.do_get_candidates()
            params = candidates[-1]
            if not re.match(r"\d{1,}-\d{1,}", params):
                params = "%d-%d" % (0, len(candidates))
            else:
                params = candidates.pop()

            return gamma_count_range(self.do_get_results(), candidates, params)

        if self.poll.get_module().module_id == 'stv':
            # we expect cached stv results
            return self.poll.stv_results

        return gamma_count_parties(self.do_get_results(), self.do_get_candidates())

    def get_results_pretty_stv(self):
        stv_results = self.poll.stv_results[0]
        candidates = self.poll.questions_data[0]['answers']
        results = {}
        winners = []
        for cand_index, round, votes_count in stv_results:
            res = {
                'name': candidates[int(cand_index)],
                'round': round,
                'count': votes_count
            }
            winners.append(res)
        results['winners'] = winners
        return results

    def get_results_pretty_score(self):
        pretty = SortedDict()

        results = self.get_results()

        for i, q in enumerate(self.poll.questions_data):
            entry = copy.copy(q)
            entry['results'] = SortedDict()
            scores = filter(lambda a: a[1].startswith("%s:" % q['question']), results['totals'])
            for score, answer in scores:
                qanswer = answer.replace("%s:" % q['question'], "")
                entry['results'][qanswer] = {
                    'score': score,
                    'scores': results['detailed'][answer]
                }
            pretty[q['question']] = entry

        pretty['meta'] = results
        results['total_cast'] = len(results['ballots'])
        return pretty

    def get_results_pretty(self):
        if self.poll.get_module().module_id == 'score':
            return self.get_results_pretty_score()

        if self.poll.get_module().module_id == 'stv':
            return self.get_results_pretty_stv()

        results = self.get_results()
        total = results['ballot_count']
        parties = []

        for count, party in results['party_counts']:
            if party is None:
                continue
                
            party_candidates = results['parties'][party]
            candidate_keys = filter(lambda x: isinstance(x, int),
                                    party_candidates.keys())
            candidate_keys.sort()
            candidates = [party_candidates[c] for c in candidate_keys]
            candidate_counts = SortedDict([(c, 0) for c in \
                                           candidates])
            candidate_sums = 0

            for candidate_count, candidate in results['candidate_counts']:
                cand_party, candidate = candidate.split(": ")

                if candidate in candidates and cand_party == party:
                    candidate_sums += count
                    candidate_counts[candidate] = candidate_count

            data = {
                'name': party.replace("{newline}", "\n").replace("{semi}", ":"),
                'total': count,
                'candidates': candidate_counts
            }

            empty_party_count = 0
            if self.poll.get_module().count_empty_question:
                for b in results['ballots']:
                    if len(b['candidates']) == 1 and \
                       party in b['parties'] and \
                       b['candidates'][0][1] not in candidates:
                            empty_party_count += 1
                data['candidates']['Χωρίς επιλογή'] = empty_party_count
            parties.append(data)

        data = {'name': u'Λευκά',
                'total': results.get('blank_count', 0)}

        if results.get('invalid_count', 0):
            data = {'name': u'Άκυρα',
                    'total': results.get('invalid_count')}
        parties.append(data)
        return parties

    def _validate_candidates(self):
        candidates = self.do_get_candidates()
        nr_candidates = len(candidates)
        if len(set(candidates)) != nr_candidates:
            m = "Duplicate candidates!"
            raise ZeusError(m)
