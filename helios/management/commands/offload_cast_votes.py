"""
move the JSON of cast votes in elections whose results were released long ago
to ballot storage (settings.STORAGES['ballots']). Fingerprints, voters and cast
times stay in the DB. Postgres only returns the space to the OS after
VACUUM FULL (or pg_repack) on helios_castvote and helios_voter.
"""

import datetime

from django.core.management.base import BaseCommand, CommandError

from helios.models import CastVote, Election

RELEASED_DAYS_AGO = 180


class Command(BaseCommand):
  help = 'offload cast vote JSON of old elections to ballot storage'

  def add_arguments(self, parser):
    parser.add_argument('--election', help='uuid of a single election to offload')
    parser.add_argument('--older-than', type=int, default=RELEASED_DAYS_AGO,
                        help='days since the result was released (default %d)' % RELEASED_DAYS_AGO)
    parser.add_argument('--dry-run', action='store_true')

  def handle(self, *args, **options):
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=options['older_than'])
    elections = Election.objects.filter(result_released_at__lt=cutoff)
    if options['election']:
      elections = elections.filter(uuid=options['election'])
      if not elections.exists():
        raise CommandError('no election %s with a result released more than %d days ago' % (options['election'], options['older_than']))

    for election in elections.only('id', 'uuid', 'short_name').order_by('id'):
      cast_votes = CastVote.objects.filter(voter__election=election, vote_offloaded_at__isnull=True)
      if options['dry_run']:
        self.stdout.write('%s: would offload %d votes' % (election.short_name, cast_votes.count()))
        continue

      offloaded = skipped = 0
      for cast_vote in cast_votes.select_related('voter').defer('voter__vote').iterator(chunk_size=100):
        cast_vote.voter.election = election
        if cast_vote.offload_vote():
          offloaded += 1
        else:
          skipped += 1
          self.stdout.write('%s: kept cast vote %d, its JSON does not match its fingerprint' % (election.short_name, cast_vote.id))
      self.stdout.write('%s: offloaded %d votes, kept %d' % (election.short_name, offloaded, skipped))
