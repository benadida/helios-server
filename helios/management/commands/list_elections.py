# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from helios import utils as helios_utils
from helios.models import *
from heliosauth.models import *

def strforce(thing):
    if isinstance(thing, unicode):
        return thing.encode('utf-8')
    return thing

class Command(BaseCommand):
    args = ''
    help = 'List elections'

    def handle(self, *args, **options):
        print ','.join(('uuid', 'όνομα', 'διαχειριστής', 'ίδρυμα',
                        'εκλέκτορες', 'ψηφίσαντες', 'έναρξη', 'λήξη'))
        for e in Election.objects.all():
            uuid = strforce(e.uuid)
            name = strforce(e.name)
            admin = strforce(e.admins.all()[0].pretty_name)
            institution = strforce(e.institution.name)
            polls = e.polls.all()
            voter_count = 0
            voted_count = 0
            for poll in e.polls.all():
                voter_count += Voter.objects.filter(poll=poll).count()
                voted_count += poll.voters_cast_count()
            voter_count = str(voter_count)
            voted_count = str(voted_count)
            start = e.voting_starts_at
            start = start.strftime("%Y-%m-%d %H:%M:%S") if start else '-'
            end = e.voting_ended_at
            end = end.strftime("%Y-%m-%d %H:%M:%S") if end else '-'
            print ','.join((uuid, name, admin, institution,
                            voter_count, voted_count, start, end))

