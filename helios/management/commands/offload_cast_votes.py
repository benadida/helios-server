"""
move the JSON of cast votes in elections whose results were released long ago
to ballot storage (settings.STORAGES['ballots']). Fingerprints, voters and cast
times stay in the DB. Postgres only returns the space to the OS after
VACUUM FULL (or pg_repack) on helios_castvote and helios_voter.
"""

import datetime

from django.core.files.storage import FileSystemStorage, storages
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from helios.models import CastVote, Election

RELEASED_DAYS_AGO = 180


class Command(BaseCommand):
  help = 'offload cast vote JSON of old elections to ballot storage'

  def add_arguments(self, parser):
    parser.add_argument('--election', help='uuid of a single election to offload')
    parser.add_argument('--older-than', type=int, default=RELEASED_DAYS_AGO,
                        help='days since the result was released (default %d)' % RELEASED_DAYS_AGO)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--allow-local-storage', action='store_true',
                        help='offload to the local filesystem (BALLOT_STORAGE_BUCKET unset)')

  def handle(self, *args, **options):
    # a machine's local disk may not outlive it, and the votes leave the DB
    if isinstance(storages['ballots'], FileSystemStorage) and not options['allow_local_storage'] and not options['dry_run']:
      raise CommandError('ballot storage is the local filesystem: set BALLOT_STORAGE_BUCKET, or pass --allow-local-storage')

    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=options['older_than'])
    elections = Election.objects.filter(result_released_at__lt=cutoff)
    if options['election']:
      elections = elections.filter(uuid=options['election'])
      if not elections.exists():
        raise CommandError('no election %s with a result released more than %d days ago' % (options['election'], options['older_than']))

    for election in elections.only('id', 'uuid', 'short_name').order_by('id'):
      # unverified votes stay: verify_cast_votes still needs to read them
      cast_votes = CastVote.objects.filter(voter__election=election, vote_offloaded_at__isnull=True).filter(Q(verified_at__isnull=False) | Q(invalidated_at__isnull=False))
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
