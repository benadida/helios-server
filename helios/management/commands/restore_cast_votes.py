"""
bring an election's offloaded cast votes back from ballot storage into the DB
"""

from django.core.management.base import BaseCommand, CommandError

from helios.models import CastVote, Election


class Command(BaseCommand):
  help = "restore an election's offloaded cast votes into the DB"

  def add_arguments(self, parser):
    parser.add_argument('election', help='election uuid')

  def handle(self, *args, **options):
    election = Election.objects.filter(uuid=options['election']).only('id', 'uuid', 'short_name').first()
    if not election:
      raise CommandError('no election %s' % options['election'])

    restored = 0
    cast_votes = CastVote.objects.filter(voter__election=election, vote_offloaded_at__isnull=False)
    for cast_vote in cast_votes.select_related('voter').defer('voter__vote').iterator(chunk_size=100):
      cast_vote.voter.election = election
      cast_vote.restore_vote()
      restored += 1
    self.stdout.write('%s: restored %d votes' % (election.short_name, restored))
