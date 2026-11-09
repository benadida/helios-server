"""
Point each voter who has voted at their latest CastVote (Voter.cast_vote),
so the copy of the vote in Voter.vote can later be dropped.

A voter is only linked to a CastVote whose vote_hash matches the voter's
and whose vote is the same as the voter's copy. Safe to re-run.
"""

import json

from django.core.management.base import BaseCommand
from django.db import connection

from helios.models import Voter

FIND_CAST_VOTES = """
SELECT v.id, v.vote_hash, cv.id, v.vote IS NULL OR cv.vote = v.vote
FROM helios_voter v
LEFT JOIN LATERAL (
  SELECT id, vote FROM helios_castvote
  WHERE voter_id = v.id AND vote_hash = v.vote_hash
  ORDER BY cast_at DESC, id DESC LIMIT 1
) cv ON true
WHERE v.id > %s AND v.vote_hash IS NOT NULL AND v.cast_vote_id IS NULL
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
    linked = missing = different = 0
    last_id = 0
    with connection.cursor() as cursor:
      while True:
        cursor.execute(FIND_CAST_VOTES, [last_id, options['batch_size']])
        rows = cursor.fetchall()
        if not rows:
          break
        last_id = rows[-1][0]

        links = []
        for voter_id, vote_hash, cast_vote_id, same_text in rows:
          if cast_vote_id is None:
            missing += 1
            self.report(options, "voter %s: no cast vote with its vote_hash" % voter_id)
          elif same_text or self.same_vote(cursor, voter_id, cast_vote_id):
            links.append((voter_id, cast_vote_id, vote_hash))
          else:
            different += 1
            self.report(options, "voter %s: cast vote %s differs from its vote copy" % (voter_id, cast_vote_id))

        if links:
          cursor.execute(LINK_CAST_VOTES.format(", ".join(["(%s, %s, %s)"] * len(links))), [x for link in links for x in link])
          linked += cursor.rowcount

    remaining = Voter.objects.exclude(vote_hash=None).filter(cast_vote=None).count()
    self.stdout.write("linked %d voters; %d without a matching cast vote, %d with a different vote; %d voters still unlinked" % (linked, missing, different, remaining))

  def same_vote(self, cursor, voter_id, cast_vote_id):
    cursor.execute("SELECT v.vote, cv.vote FROM helios_voter v, helios_castvote cv WHERE v.id = %s AND cv.id = %s", [voter_id, cast_vote_id])
    voter_vote, cast_vote = cursor.fetchone()
    return json.loads(voter_vote) == json.loads(cast_vote)

  def report(self, options, message):
    if options['verbosity'] >= 2:
      self.stdout.write(message)
