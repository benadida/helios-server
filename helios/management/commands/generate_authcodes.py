"""
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from helios.models import *
from zeus.models import generate_authcodes
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

class Command(BaseCommand):
    args = ''
    help = "Generate authcodes for (a subset of voters of) an election"

    @transaction.commit_on_success
    def handle(self, *args, **options):
        argc = len(args)
        if argc < 1:
            print "usage: generate_authocdes <election_uuid> [voter_login...]"
            raise SystemExit

        uuid = args[0]
        voter_logins = args[1:]
        generate_authcodes(uuid, voter_logins)

