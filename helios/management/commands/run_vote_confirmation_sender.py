import time
from django.core.management.base import BaseCommand
from django.db import OperationalError, close_old_connections
from django.db.models import Count
from helios.models import VoteConfirmationEmail
from helios.vote_confirmation import deliver_next_confirmation

class Command(BaseCommand):
    help = 'Deliver verified-vote confirmations from the durable outbox.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true')
        parser.add_argument('--status', action='store_true')

    def handle(self, *args, **options):
        if options['status']:
            for row in VoteConfirmationEmail.objects.values('state').annotate(total=Count('id')).order_by('state'):
                self.stdout.write(f"{row['state']}: {row['total']}")
            return
        while True:
            close_old_connections()
            try:
                if deliver_next_confirmation():
                    time.sleep(0.6)
                    continue
                if options['once']:
                    return
            except OperationalError:
                self.stderr.write('Confirmation database unavailable; retrying.')
                if options['once']:
                    raise
            time.sleep(2)
