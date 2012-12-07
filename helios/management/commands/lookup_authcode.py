"""
"""
from django.core.management.base import BaseCommand

from helios.models import *
from zeus.models import lookup_authcode
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

class Command(BaseCommand):
    args = ''
    help = "Get voter login url by authcode"

    def handle(self, *args, **options):
        argc = len(args)
        if argc < 1:
            print "usage: lookup_authcode <authcodes...>"
            raise SystemExit

        for authcode in args:
            r = lookup_authcode(authcode)
            if r is None:
                print '%s   %s' % (authcode, 'NOT FOUND')
                continue

            election_uuid, voter_login = r
	    e = Election.objects.get(uuid=election_uuid)
            voter = Voter.objects.get(election=e,
                                      voter_login_id=voter_login)
            print '%s   %s' % (authcode, voter.get_quick_login_url())
