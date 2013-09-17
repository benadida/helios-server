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
        print ','.join(('uuid ψηφοφορίας', 'όνομα ψηφοφορίας',
                        'uuid κάλπης', 'όνομα κάλπης',
                        'διαχειριστής', 'ίδρυμα', 'εκλέκτορες',
                        'ψηφίσαντες', 'έναρξη', 'λήξη'))
        for e in Election.objects.all():
            uuid = strforce(e.uuid)
            name = strforce(e.name)
            admins = list(e.admins.all())
            admin = strforce(admins[0].pretty_name) if admins else ''
            institution = strforce(e.institution.name)
            polls = e.polls.all()
            for poll in e.polls.all():
                poll_name = strforce(poll.name)
                poll_uuid = strforce(poll.uuid)
                voter_count = str(Voter.objects.filter(poll=poll).count())
                voted_count = str(poll.voters_cast_count())
                start = e.voting_starts_at
                start = start.strftime("%Y-%m-%d %H:%M:%S") if start else '-'
                end = e.voting_ended_at
                end = end.strftime("%Y-%m-%d %H:%M:%S") if end else '-'
                print ','.join((uuid, name, poll_uuid, poll_name,
                                admin, institution, voter_count, voted_count,
                                start, end))

