"""
Point each voter who has voted at their latest CastVote (Voter.cast_vote),
so the copy of the vote in Voter.vote can later be dropped.

A voter is only linked to a CastVote whose vote_hash matches the voter's
and whose vote is the same as the voter's copy. Safe to re-run.
"""

import json

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import Q

from helios.models import Voter

FIND_CAST_VOTES = """
SELECT v.id, v.vote_hash, v.vote IS NULL, cv.id, cv.vote = v.vote
FROM helios_voter v
LEFT JOIN LATERAL (
  SELECT id, vote FROM helios_castvote
  WHERE voter_id = v.id AND vote_hash = v.vote_hash AND v.vote IS NOT NULL
  ORDER BY cast_at DESC, id DESC LIMIT 1
) cv ON true
WHERE v.id > %s AND (v.vote_hash IS NOT NULL OR v.vote IS NOT NULL) AND v.cast_vote_id IS NULL
ORDER BY v.id LIMIT %s
"""

# skip voters who cast a new vote since we looked
LINK_CAST_VOTES = """
UPDATE helios_voter AS v SET cast_vote_id = x.cast_vote_id
FROM (VALUES {}) AS x(id, cast_vote_id, vote_hash)
WHERE v.id = x.id AND v.cast_vote_id IS NULL AND v.vote_hash = x.vote_hash
"""


class Command(BaseCommand):
  help = "Link voters to their latest cast vote"

  def add_arguments(self, parser):
    parser.add_argument('--batch-size', type=int, default=1000)

  def handle(self, *args, **options):
    linked = missing = different = no_hash = 0
    last_id = 0
    with connection.cursor() as cursor:
      while True:
        cursor.execute(FIND_CAST_VOTES, [last_id, options['batch_size']])
        rows = cursor.fetchall()
        if not rows:
          break
        last_id = rows[-1][0]

        links = []
        for voter_id, vote_hash, no_copy, cast_vote_id, same_text in rows:
          if vote_hash is None:
            # still counted by the tally, so it needs a look before Voter.vote goes
            no_hash += 1
            self.report(options, "voter %s: has a vote copy but no vote_hash" % voter_id)
          elif no_copy:
            missing += 1
            self.report(options, "voter %s: has a vote_hash but no vote copy" % voter_id)
          elif cast_vote_id is None:
            missing += 1
            self.report(options, "voter %s: no cast vote matching its vote copy" % voter_id)
          elif same_text or self.same_vote(cursor, voter_id, cast_vote_id):
            links.append((voter_id, cast_vote_id, vote_hash))
          else:
            different += 1
            self.report(options, "voter %s: cast vote %s differs from its vote copy" % (voter_id, cast_vote_id))

        if links:
          cursor.execute(LINK_CAST_VOTES.format(", ".join(["(%s, %s, %s)"] * len(links))), [x for link in links for x in link])
          linked += cursor.rowcount

    remaining = Voter.objects.filter(cast_vote=None).filter(Q(vote_hash__isnull=False) | Q(vote__isnull=False)).count()
    self.stdout.write("linked %d voters; %d without a matching cast vote, %d with a different vote, %d without a vote_hash; %d voters still unlinked" % (linked, missing, different, no_hash, remaining))

  def same_vote(self, cursor, voter_id, cast_vote_id):
    cursor.execute("SELECT v.vote, cv.vote FROM helios_voter v, helios_castvote cv WHERE v.id = %s AND cv.id = %s", [voter_id, cast_vote_id])
    voter_vote, cast_vote = cursor.fetchone()
    return json.loads(voter_vote) == json.loads(cast_vote)

  def report(self, options, message):
    if options['verbosity'] >= 2:
      self.stdout.write(message)
