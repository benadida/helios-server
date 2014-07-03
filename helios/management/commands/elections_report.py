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
    help = 'Elections report'

    def handle(self, *args, **options):
        print '|'.join(('ΙΔΡΥΜΑ', 'ΕΚΛΕΚΤΟΡΕΣ',
                        'ΨΗΦΙΣΑΝΤΕΣ', 'ΕΝΑΡΞΗ', 'ΛΗΞΗ',
                        'uuid', 'ΌΝΟΜΑ', 'admin'))

        for e in Election.objects.filter(trial=False).exclude(institution__name__in=('HELPDESK', 'ZEUS-DEV')).order_by('voting_starts_at'):
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
                if voted_count < 10:
                    continue

                start = e.voting_starts_at
                if not start:
                    continue

                start = start.strftime("%Y-%m-%d %H:%M")
                end = e.voting_ended_at
                if not end:
                    continue

                end = e.voting_end_date
                end = end.strftime("%Y-%m-%d %H:%M")
                if not poll.result:
                    continue

		print '|'.join((institution, voter_count, voted_count, start,
                                end, poll_uuid, poll_name, admin))

