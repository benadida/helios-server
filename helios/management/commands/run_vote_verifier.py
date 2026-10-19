"""Recover and verify saved votes; run as a supervised background process."""
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import OperationalError, close_old_connections
from django.db.models import Count

from helios.models import VoteVerificationJob
from helios.vote_verification import database_queue_enabled, process_next_job, recover_pending_jobs


class Command(BaseCommand):
    help = 'Run the durable vote verification worker (PostgreSQL required).'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Drain currently due jobs and exit.')
        parser.add_argument('--poll-interval', type=float, default=2,
                            help='Idle wait between probes, in seconds (0.1–60).')
        parser.add_argument('--status', action='store_true',
                            help='Report aggregate job states and exit; no voter data.')

    def handle(self, *args, **options):
        if not database_queue_enabled():
            raise CommandError('Set ALU_VOTE_VERIFICATION_BACKEND=database to run this worker.')
        if options['status']:
            counts = dict(VoteVerificationJob.objects.values('state')
                          .annotate(total=Count('pk')).values_list('state', 'total'))
            for state in ('pending', 'complete', 'failed'):
                self.stdout.write(f'{state}: {counts.get(state, 0)}')
            return
        interval = options['poll_interval']
        if not 0.1 <= interval <= 60:
            raise CommandError('poll-interval must be between 0.1 and 60 seconds.')
        recover = True
        while True:
            close_old_connections()
            try:
                if recover:
                    recover_pending_jobs()
                    recover = False
                if process_next_job():
                    continue
                if options['once']:
                    return
            except OperationalError:
                # Do not log connection strings or exception text. Recover again
                # after reconnection; any interrupted transaction was rolled back.
                close_old_connections()
                recover = True
                self.stderr.write('Vote verifier database unavailable; retrying.')
                if options['once']:
                    raise CommandError('Vote verifier database unavailable.') from None
            time.sleep(interval)
