"""
put background tasks back in the queue when their worker died mid-task,
leaving them RUNNING forever
"""

import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone
from django_tasks import TaskResultStatus
from django_tasks_db.models import DBTaskResult

# re-running these would email every voter again
NOT_REQUEUED = ['helios.tasks.voters_email', 'helios.tasks.voters_notify']

STUCK_AFTER_MINUTES = 120


class Command(BaseCommand):
  help = 'requeue background tasks that have been running for too long'

  def add_arguments(self, parser):
    parser.add_argument('--older-than', type=int, default=STUCK_AFTER_MINUTES,
                        help='minutes a task must have been running; longer than the longest tally (default %d)' % STUCK_AFTER_MINUTES)
    parser.add_argument('--dry-run', action='store_true')

  def handle(self, *args, **options):
    cutoff = timezone.now() - datetime.timedelta(minutes=options['older_than'])
    stuck = DBTaskResult.objects.running().filter(started_at__lt=cutoff)

    for task_path in NOT_REQUEUED:
      for task_result in stuck.filter(task_path=task_path):
        self.stdout.write('not requeued: %s %s' % (task_result.id, task_path))

    to_requeue = stuck.exclude(task_path__in=NOT_REQUEUED)
    if options['dry_run']:
      self.stdout.write('would requeue %d tasks' % to_requeue.count())
      return

    count = to_requeue.update(status=TaskResultStatus.READY, started_at=None)
    self.stdout.write('requeued %d tasks' % count)
