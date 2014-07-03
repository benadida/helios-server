import csv, datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from helios import utils as helios_utils
from helios.models import Poll, Voter

class Command(BaseCommand):
    args = ''
    help = 'List election polls'

    def handle(self, *args, **options):
        polls = Poll.objects.filter()
        if args:
            polls = polls.filter(election__uuid=args[0])

        for p in polls:
            print p.uuid, p.short_name
