# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from helios.models import *
from heliosauth.models import *

from zeus.core import *

def strforce(thing):
    if isinstance(thing, unicode):
        return thing.encode('utf-8')
    return str(thing)

class Command(BaseCommand):
    args = ''
    help = 'Ballot report'

    def handle(self, *args, **options):
        poll_uuid = args[0]

        poll = Poll.objects.get(uuid=poll_uuid)
        ballots = poll.result[0]
        candidates = poll.questions_data[0]['answers']
        nr_cand = len(candidates)
        results = '\n'.join(
                '|'.join(strforce(candidates[x]).replace('|', '^')
                         for x in to_absolute_answers(
                                gamma_decode(ballot, nr_cand, nr_cand), nr_cand))
                for ballot in ballots)
        print results
