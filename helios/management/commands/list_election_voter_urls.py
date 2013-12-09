import csv, datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from helios import utils as helios_utils
from helios.models import Poll, Voter

class Command(BaseCommand):
    args = ''
    help = 'List the voter login urls'

    def handle(self, *args, **options):
        if args:
            voters = Voter.objects.filter(poll__election__uuid=args[0])
        else:
            voters = Voter.objects.all()

        for v in voters:
            print v.get_quick_login_url()
        # once broken out of the while loop, quit and wait for next invocation
        # this happens when there are no votes left to verify

