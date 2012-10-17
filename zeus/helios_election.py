import datetime
import uuid
import json

from zeus.core import ZeusCoreElection, Teller, sk_from_args, mix_ciphers
from zeus.core import V_CAST_VOTE, V_PUBLIC_AUDIT, V_AUDIT_REQUEST

from zeus.models import ElectionInfo
from helios import models as helios_models
from helios.views import ELGAMAL_PARAMS
from helios import datatypes
from django.conf import settings
from helios.crypto import electionalgs
from helios.crypto import utils


class NullStream(object):
    def read(*args):
        return ''
    def write(*args):
        return


def get_datatype(datatype, obj=None, **kwargs):
    if len(datatype.split("/")) == 1:
        datatype = 'legacy/%s' % datatype

    obj = obj or kwargs
    return datatypes.LDObject.fromDict(obj, type_hint=datatype)


class HeliosElection(ZeusCoreElection):

    def __init__(self, *args, **kwargs):
        if kwargs.get('model', None):
            self.model = kwargs.pop('model')
            kwargs.pop('uuid', None)
        else:
            self.model, created = ElectionInfo.objects.get_or_create(uuid=kwargs.pop('uuid'))
        kwargs['cryptosystem'] = (ELGAMAL_PARAMS.p, ELGAMAL_PARAMS.g,
                                  ELGAMAL_PARAMS.q)
        kwargs['teller'] = Teller(outstream=NullStream())
        super(HeliosElection, self).__init__(*args, **kwargs)

    def _get_zeus_vote(self, enc_vote, voter=None, audit_password=None):
        return self.model.election._get_zeus_vote(enc_vote, voter=voter,
                                                  audit_password=audit_password)

    def do_get_vote(self, fingerprint):
        # try CastVote
        try:
            vote = self.model.election.castvote_set.get(fingerprint=fingerprint)
            zeus_vote = self._get_zeus_vote(vote.vote)
            zeus_vote['fingerprint'] = vote.fingerprint
            zeus_vote['signature'] = vote.signature
            zeus_vote['previous'] = vote.previous
            zeus_vote['voter'] = vote.voter.uuid
            zeus_vote['index'] = vote.index
            return zeus_vote
        except helios_models.CastVote.DoesNotExist:
            pass
        # then AuditedBallot
        try:
            audited = self.model.election.auditedballot_set.get(
                fingerprint=fingerprint, is_request=False)
            helios_vote = electionalgs.EncryptedVote.fromJSONDict(
                utils.from_json(audited.raw_vote))
            zeus_vote = self._get_zeus_vote(
                helios_vote,
                audit_password=audited.audit_code)
            zeus_vote['fingerprint'] = audited.fingerprint
            zeus_vote['signature'] = audited.signature
            return zeus_vote
        except helios_models.AuditedBallot.DoesNotExist:
            return None
        return None

    def do_get_cast_votes(self, voter):
        votes = []
        for vote in self.model.election.castvote_set.filter(verified_at__isnull=False,
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
        index = self.model.election.castvote_set.filter(verified_at__isnull=False).count()
        return index

    def do_get_index_vote(self, index):
        return self.model.election.castvote_set.get(index=index).fingerprint

    def do_get_vote_index(self):
        votes = []
        for vote in self.model.election.castvote_set.filter(index__isnull=False).order_by('index'):
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
        for audited in self.model.election.auditedballot_set.filter(is_request=False):
            helios_vote = electionalgs.EncryptedVote.fromJSONDict(
                utils.from_json(audited.raw_vote))
            zeus_vote = self._get_zeus_vote(
                helios_vote,
                audit_password=audited.audit_code)
            zeus_vote['fingerprint'] = audited.fingerprint
            zeus_vote['signature'] = audited.signature
            votes[audited.fingerprint] = zeus_vote
        return votes

    def _casted_votes(self):
        votes = {}
        for vote in self.model.election.castvote_set.filter(verified_at__isnull=False):
            zeus_vote = self._get_zeus_vote(vote.vote, voter=vote.voter)
            zeus_vote['fingerprint'] = vote.fingerprint
            zeus_vote['signature'] = vote.signature
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
        for req in self.model.election.auditedballot_set.filter(is_request=True):
            reqs[req.fingerprint] = req.voter.uuid
        return reqs

    def do_get_audit_request(self, fingerprint):
        try:
            obj = self.model.election.auditedballot_set.get(
                fingerprint=fingerprint,
                is_request=True)
        except helios_models.AuditedBallot.DoesNotExist:
            return None
        return obj.voter.uuid

    def do_get_audit_publications(self):
        pubs = []
        for pub in self.model.election.auditedballot_set.filter(is_request=False):
            pubs.append(pub.fingerprint)

        return pubs

    def _get_helios_vote_dict(self, vote):
        enc_ballot = vote['encrypted_ballot']
        ballot = {
            'election_hash': self.model.election.hash,
            'election_uuid': self.model.election.uuid,
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
        vobj.election = self.model.election
        vobj.vote_hash = vote_hash
        vobj.cast_at = datetime.datetime.now()
        vobj.verified_at = datetime.datetime.now()
        vobj.fingerprint = vote['fingerprint']
        vobj.signature = vote['signature']
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
        vobj.election = self.model.election
        vobj.vote_hash = enc_vote.get_hash()
        vobj.fingerprint = vote['fingerprint']
        vobj.is_request = True
        vobj.audit_code = vote['audit_code']
        vobj.signature = vote['signature']
        vobj.voter = self._get_voter_object(vote['voter'])

        vobj.save()

    def _do_store_public_audit(self, vote):
        vobj = helios_models.AuditedBallot.objects.get(election=self.model.election,
                                                       fingerprint=vote['fingerprint'],
                                                       is_request=True)
        vobj.pk = None
        vobj.signature = vote['signature']
        vobj.fingerprint = vote['fingerprint']
        vobj.is_request = False
        vobj.voter = None
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
            return self.model.election.questions[0]['answers']
        except:
            return []

    def _get_voter_object(self, voter_uuid):
        return self.model.election.voter_set.get(uuid=voter_uuid)

    def do_get_voter(self, voter_uuid):
	v = self._get_voter_object(voter_uuid)
        return v.voter_name + u" " + v.voter_surname

    def do_get_voters(self):
        voters = {}
        for v in self.model.election.voter_set.all():
            voters[v.uuid] = v.voter_name + u" " + v.voter_surname

        return voters

    def do_store_election_public(self, public):
        p, g, q = self.do_get_cryptosystem()
        pk = get_datatype('EGPublicKey', p=p, g=g, q=q, y=public)
        election = self.model.election
        election.public_key = pk
        election.save()

    def do_get_election_public(self):
        if self.model.election.public_key:
            return self.model.election.public_key.y
        return None

    def do_get_voter_audit_codes(self, voter):
        return self.model.election.voter_set.get(
            uuid=voter).get_audit_passwords()

    def do_get_all_voter_audit_codes(self):
        voter_slots = {}
        for v in self.model.election.voter_set.all():
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
            election=self.model.election,
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

        pok = get_datatype('DLogProof', commitment=commitment, challenge=challenge,
                                         response=response)
        trustee.pok = pok
        trustee.save()

    def do_get_zeus_key(self):
        t = self.model.election.get_helios_trustee()
        args = self.do_get_cryptosystem()
        args += [t.secret_key.x, t.public_key.y]
        args += (t.pok.commitment, t.pok.challenge, t.pok.response)
        return sk_from_args(*args)

    def do_get_zeus_secret(self):
        trustee = self.model.election.get_helios_trustee()
        return trustee.secret_key.x if trustee else None

    def do_get_zeus_public(self):
        trustee = self.model.election.get_helios_trustee()
        return trustee.public_key.y if trustee else None

    def do_get_zeus_key_proof(self):
        trustee = self.model.election.get_helios_trustee()
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
            public_key_hash=pk.hash, election=self.model.election)
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
        t = helios_models.Trustee.objects.get(public_key_hash=pk.hash)
        return [t.pok.commitment, t.pok.challenge, t.pok.response]

    def do_get_trustees(self):
        trustees = self.model.election.trustee_set.filter(
            secret_key__isnull=True, public_key__isnull=False)
        zeus_trustees = {}

        for t in trustees:
          public = t.public_key.y
          zeus_trustees[public] = [t.pok.commitment, t.pok.challenge,
                                   t.pok.response]
        return zeus_trustees

    def do_get_all_trustee_factors(self):
        factors = {}
        for trustee in self.model.election.trustee_set.filter(
            secret_key__isnull=True):
          factors[trustee.public_key.y] = self._get_zeus_factors(trustee)
        return factors


    def do_get_last_mix(self):
        mixnet = helios_models.ElectionMixnet.objects.filter(
            election=self.model.election,
            status='finished').order_by('-mix_order')

        if mixnet.count() == 0:
            return self.extract_votes_for_mixing()

        return mixnet[0].zeus_mix()

    def do_get_all_mixes(self):
        mixes = [self.extract_votes_for_mixing()]
        for mixnet in self.model.election.mixnets.filter():
          mixes.append(mixnet.mix)
        return mixes

    def mix(self, ciphers):
        return mix_ciphers(ciphers, teller=self.teller)

    def _get_zeus_factors(self, trustee):
        trustee_factors = []
        for index, factor in enumerate(trustee.decryption_factors[0]):
            zeus_factor = []
            proof = trustee.decryption_proofs[0][index]
            zeus_factor.append(factor)
            proof = [proof.commitment['A'],
                     proof.commitment['B'],
                     proof.challenge,
                     proof.response]
            zeus_factor.append(proof)
            trustee_factors.append(zeus_factor)

        return trustee_factors

    def do_get_zeus_factors(self):
        trustee = self.model.election.get_helios_trustee()
        return self._get_zeus_factors(trustee)

    def do_store_zeus_factors(self, factors):
        t = self.model.election.get_helios_trustee()
        helios_factors = [[]]
        helios_proofs = [[]]

        for factor in factors:
          proof_obj = get_datatype('EGZKProof',{
            'commitment': {'A':factor[1][0], 'B': factor[1][1]},
            'challenge': factor[1][2],
            'response': factor[1][3]
          })
          helios_factors[0].append(factor[0])
          helios_proofs[0].append(proof_obj)

        t.decryption_factors = helios_factors
        t.decryption_proofs = helios_proofs
        t.save()

    def do_store_results(self, results):
        e = self.model.election
        e.result = get_datatype('phoebus/Result', [results])
        e.save()

    @classmethod
    def mk_random(cls, *args, **kwargs):
        helios_models.Election.objects.create(uuid=kwargs.get('uuid'))
        super(cls, HeliosElection).mk_random(*args, **kwargs)


    #def do_store_candidates(self, candidates):
        #e = self.model.election
        #if not e.questions:
            #e.questions = [{
                #'answers': candidates,
                #'choice_type': 'stv',
                #'result_type': 'absolute', 'tally_type': 'stv'}]
            #e.save()

