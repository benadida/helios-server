"""
verify cast votes that have not yet been verified

Ben Adida
ben@adida.net
2010-05-22
"""
import csv, datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from helios import utils as helios_utils
from helios.models import *

class Command(BaseCommand):
    args = ''
    help = 'Show the voter login url'

    def handle(self, *args, **options):
        for v in Voter.objects.filter(voter_email=args[0]):
            print v.election.uuid, v.get_quick_login_url()
        # once broken out of the while loop, quit and wait for next invocation
        # this happens when there are no votes left to verify

