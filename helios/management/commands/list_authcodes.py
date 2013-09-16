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
        for voter in poll.voters.filter():
            regid = "%d-%s" % (poll_pk, voter.voter_login_id)
            email = voter.voter_email
            secret = voter.voter_password
            print '%s %s %s' % (regid, email, secret)
