"""
"""
import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.timesince import timesince

from helios import utils as helios_utils
from helios.models import *

class Command(BaseCommand):
    args = ''
    help = 'Show election status'

    def handle(self, *args, **options):
        if not args:
            now = datetime.datetime.now()
            args = Election.objects.filter(voting_starts_at__lt=now, voting_ends_at__gt=now)
            args = args.values_list('uuid', flat=True)

        for uuid in args:
            try:
                election = Election.objects.get(uuid=uuid)
                polls = election.polls.all()
            except Election.DoesNotExist:
                polls = (Poll.objects.get(uuid=uuid),)

            for poll in polls:
                frozen_at = poll.election.frozen_at
                starts_at = poll.election.voting_starts_at
                ends_at = poll.election.voting_ends_at
                extended_until = poll.election.voting_extended_until
                ended_at = poll.election.voting_ended_at
                canceled_at = poll.election.canceled_at
                last_visit_at = poll.last_voter_visit()
                if last_visit_at is not None:
                    last_visit_text = last_visit_at.strftime("%Y-%m-%d %H:%M:%S") + \
                            " (%s ago)" % (timesince(last_visit_at))
                else:
                    last_visit_text = 'none'

                print "election name:        ", poll.election.name
                print "poll name:            ", poll.name
                print "election uuid:        ", poll.election.uuid
                print "poll uuid:            ", poll.uuid
                print "admin:                ", poll.election.admins.all()[0].pretty_name
                print "institution:          ", poll.election.institution.name
                print "frozen_at:            ", frozen_at and frozen_at.strftime("%Y-%m-%d %H:%M:%S")
                print "voting_starts_at:     ", starts_at and starts_at.strftime("%Y-%m-%d %H:%M:%S")
                print "voting_ends_at:       ", ends_at and ends_at.strftime("%Y-%m-%d %H:%M:%S")
                print "voting_extended_until:", extended_until and extended_until.strftime("%Y-%m-%d %H:%M:%S")
                print "voting_ended_at:      ", ended_at and ended_at.strftime("%Y-%m-%d %H:%M:%S")
                print "canceled_at:          ", canceled_at and canceled_at.strftime("%Y-%m-%d %H:%M:%S")
                print "voters:               ", poll.voters.count()
                print "counted votes:         %d/%d" % (poll.voters_cast_count(), poll.cast_votes.count())
                print "voters visits:        ", poll.voters_visited_count()
                print "last voter visit:     ", last_visit_text
                print ""

