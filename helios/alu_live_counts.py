"""Private, provisional aggregate counts. Never decrypt an individual ballot.

Only already verified/counted votes contribute. Final eligibility review and the
normal trustee tally remain authoritative. No election/trustee state is changed.
"""
import datetime
import hashlib
import json

from django.core.cache import cache
from django.db import connection
from django.db.models import BooleanField, ExpressionWrapper, Q

from helios import datatypes, models
from helios.crypto import algs


def live_candidate_counts(election):
  if not election.frozen_at or not election.questions:
    return {'positions': None, 'counts_status': 'not_ready'}
  if models.BallotPolicyReview.objects.filter(election=election, decision='pending').exists():
    return {'positions': None, 'counts_status': 'review_needed'}
  # External trustees retain control of their keys. A cached snapshot must not
  # survive a key being removed, and no new key/contribution is ever generated.
  trustees = list(election.trustee_set.annotate(has_secret=ExpressionWrapper(Q(secret_key__isnull=False), output_field=BooleanField())).order_by('id').values_list('id', 'public_key_hash', 'has_secret'))
  if not trustees or any(not row[2] for row in trustees):
    return {'positions': None, 'counts_status': 'trustees_required'}
  namespace = hashlib.sha256(json.dumps([str(election.uuid), str(election.frozen_at),
    election.questions, trustees], sort_keys=True).encode()).hexdigest()
  key = 'alu:provisional-counts:v1:' + namespace
  previous = cache.get(key)
  # Compare one small DB-side digest, rather than transferring every stored hash
  # on every dashboard poll. Full metadata is read only when a vote changes.
  with connection.cursor() as cursor:
    cursor.execute("""select md5(coalesce(string_agg(id::text || ':' || coalesce(vote_hash,''), ',' order by id),''))
      from helios_voter where election_id=%s and vote is not null""", [election.pk])
    revision = cursor.fetchone()[0]
  if previous and previous.get('revision') == revision:
    return previous['response']
  records = list(election.voter_set.exclude(vote=None).order_by('id').values_list('id', 'vote_hash'))

  # Carry forward only an encrypted aggregate and hash metadata, never per-voter
  # decrypted choices. A replaced/deleted/reordered counted ballot forces rebuild.
  reusable = bool(previous and len(previous['records']) <= len(records) and
    records[:len(previous['records'])] == previous['records'])
  if reusable:
    tally = datatypes.LDObject.fromDict(previous['tally'], type_hint='legacy/Tally').wrapped_obj
    tally.init_election(election)
    for row in tally.tally:
      for ciphertext in row:
        ciphertext.pk = tally.public_key
    new_records = records[len(previous['records']):]
  else:
    tally = election.init_tally()
    new_records = records
  if new_records:
    # Proofs were checked before Voter.vote was stored. Read ciphertext choices
    # only: no identities, email addresses, proofs or plaintext/randomness.
    with connection.cursor() as cursor:
      cursor.execute("""select v.id, v.vote_hash,
        (select jsonb_agg(answer->'choices' order by ordinal)
         from jsonb_array_elements(v.vote::jsonb->'answers') with ordinality a(answer,ordinal))
        from helios_voter v where v.election_id=%s and v.vote is not null and v.id=any(%s)
        order by v.id""", [election.pk, [row[0] for row in new_records]])
      rows = cursor.fetchall()
    if [(row[0], row[1]) for row in rows] != new_records:
      return {'positions': None, 'counts_status': 'unavailable'}
    for _, _, choices in rows:
      if isinstance(choices, str):
        choices = json.loads(choices)
      if not isinstance(choices, list) or len(choices) != len(election.questions):
        raise ValueError('Counted ballot shape mismatch.')
      for i, question in enumerate(election.questions):
        if not isinstance(choices[i], list) or len(choices[i]) != len(question['answers']):
          raise ValueError('Counted ballot shape mismatch.')
        for j, ciphertext in enumerate(choices[i]):
          value = datatypes.LDObject.fromDict(ciphertext, type_hint='legacy/EGCiphertext').wrapped_obj
          value.pk = tally.public_key
          tally.tally[i][j] = value * tally.tally[i][j]
      tally.num_tallied += 1
  if tally.num_tallied != len(records):
    raise ValueError('Counted aggregate shape mismatch.')

  # Verify the complete set of held keys belongs to this frozen public key.
  # Factors exist only in this request, for the homomorphic sum, never a voter.
  factors = []
  product = 1
  for trustee in election.trustee_set.only('public_key', 'secret_key'):
    pk, sk = trustee.public_key, trustee.secret_key
    if sk is None or pk is None or (pk.p, pk.q, pk.g) != (tally.public_key.p, tally.public_key.q, tally.public_key.g):
      return {'positions': None, 'counts_status': 'trustees_required'}
    if pow(pk.g, sk.x, pk.p) != pk.y:
      raise ValueError('Trustee key mismatch.')
    product = product * pk.y % pk.p
    contribution, proofs = tally.decryption_factors_and_proofs(sk)
    if not tally.verify_decryption_proofs(contribution, proofs, pk, algs.EG_fiatshamir_challenge_generator):
      raise ValueError('Aggregate decryption proof failed.')
    factors.append(contribution)
  if product != tally.public_key.y:
    return {'positions': None, 'counts_status': 'trustees_required'}
  counts = tally.decrypt_from_factors(factors, tally.public_key)
  if any(type(n) is not int or n < 0 or n > tally.num_tallied for row in counts for n in row) or any(sum(row) > tally.num_tallied for row in counts):
    raise ValueError('Aggregate count unavailable.')
  response = {'counts_status': 'live', 'counted_votes': tally.num_tallied,
    'counts_updated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'positions': [{'name': q.get('short_name') or q['question'], 'candidates': [
      {'name': name, 'votes': counts[i][j]} for j, name in enumerate(q['answers'])]}
      for i, q in enumerate(election.questions)]}
  cache.set(key, {'records': records, 'revision': hashlib.md5(','.join(str(pk) + ':' + (vote_hash or '') for pk, vote_hash in records).encode()).hexdigest(), 'tally': datatypes.LDObject.instantiate(tally, datatype='legacy/Tally').toDict(),
    'response': response}, timeout=300)
  return response
