# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from helios.models import *
from heliosauth.models import *

def strforce(thing):
    if isinstance(thing, unicode):
        return thing.encode('utf-8')
    return thing

class Command(BaseCommand):
    args = ''
    help = 'Poll report'

    def handle(self, *args, **options):
        poll_uuid = args[0]

        poll = Poll.objects.get(uuid=poll_uuid)
        print poll.election.institution.name
        print poll.name
        print "start:", poll.election.voting_starts_at
        print "ended:", poll.election.voting_ended_at

        # counted_fingerprints = poll.extract_votes_for_mixing()[1]
        # counted_votes = poll.cast_votes.filter(fingerprint__in=counted_fingerprint)
        counted_votes = poll.cast_votes.all()
        voter_counts = {}
        for v in counted_votes:
            voter_id = v.voter.voter_login_id
            if voter_id not in voter_counts:
                voter_counts[voter_id] = 0
            voter_counts[voter_id] += 1

        output = []
        for v in counted_votes:
            voter_id = v.voter.voter_login_id
            count = voter_counts[voter_id]
            timestamp = v.cast_at.strftime('%Y-%m-%d %H:%M:%S.%f')
            t = ((-count, timestamp), (voter_id, v.voter.voter_surname,
                                       v.voter.voter_name, v.voter.voter_fathername,
                                       v.voter.voter_email, v.fingerprint))
            output.append(t)

        output.sort()
        output = [(t,) + x + (-c,) for (c,t), x in output]

        for t in output:
            print '|'.join(str(x) for x in t)

