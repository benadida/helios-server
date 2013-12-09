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
    help = "List authcodes for (a subset of voters of) a poll"

    @transaction.commit_on_success
    def handle(self, *args, **options):
        argc = len(args)
        if argc < 1:
            print "usage: list_authocdes <poll_uuid> [voter_login...]"
            raise SystemExit

        uuid = args[0]
        poll = Poll.objects.get(uuid=uuid)
        poll_pk = poll.pk
        voter_logins = args[1:]
        print '%20s %7s %25s %12s' % ("Login code", "Reg num", "Email", "Secret")
        print '%20s %7s %25s %12s' % ("==========", "=======", "=====", "======")
        for voter in poll.voters.filter():
            logincode = voter.login_code
            email = voter.voter_email
            secret = voter.voter_password
            regid = voter.voter_login_id
            print '%20s %7s %25s %12s' % (logincode, regid, email, secret)
