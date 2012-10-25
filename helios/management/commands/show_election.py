"""
"""
import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from helios import utils as helios_utils
from helios.models import *

class Command(BaseCommand):
    args = ''
    help = 'Show election status'

    def handle(self, *args, **options):
        if not args:
            raise ValueError("No election uuid given")

        election = Election.objects.get(uuid=args[0])

        frozen_at = election.frozen_at
        starts_at = election.voting_starts_at
        started_at = election.voting_started_at
        ends_at = election.voting_ends_at
        extended_until = election.voting_extended_until
        ended_at = election.voting_ended_at

        print "uuid:                 ", election.uuid
        print "admin:                ", election.admins.all()[0].pretty_name
        print "name:                 ", election.name
        print "institution:          ", election.institution.name
        print "frozen_at:            ", frozen_at and frozen_at.strftime("%Y-%m-%d %H:%M:%S")
        print "voting_starts_at:     ", starts_at and starts_at.strftime("%Y-%m-%d %H:%M:%S")
        print "voting_started_at:    ", started_at and started_at.strftime("%Y-%m-%d %H:%M:%S")
        print "voting_ends_at:       ", ends_at and ends_at.strftime("%Y-%m-%d %H:%M:%S")
        print "voting_extended_until:", extended_until and extended_until.strftime("%Y-%m-%d %H:%M:%S")
        print "voting_ended_at:      ", ended_at and ended_at.strftime("%Y-%m-%d %H:%M:%S")
        print "voters:               ", election.voter_set.count()
        print "cast votes:           ", election.castvote_set.count()

