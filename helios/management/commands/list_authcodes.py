"""
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from helios.models import *
from zeus.models import list_authcodes
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

class Command(BaseCommand):
    args = ''
    help = "List authcodes for (a subset of voters of) an election"

    @transaction.commit_on_success
    def handle(self, *args, **options):
        argc = len(args)
        if argc < 1:
            print "usage: list_authocdes <election_uuid> [voter_login...]"
            raise SystemExit

        uuid = args[0]
        voter_logins = args[1:]
        authcodes = list_authcodes(uuid, voter_logins)
        for voter_login, authcode in authcodes:
            print '%s	%s' % (voter_login, authcode)
