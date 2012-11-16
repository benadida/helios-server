from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from heliosauth.models import *

import pprint

class Command(BaseCommand):
    args = ''
    help = 'List users'


    def handle(self, *args, **options):
        info = False
        if len(args) > 0 and args[0] == "1":
            info = True

        for u in User.objects.values("user_id","ecounting_account",
                                     "info").order_by('user_id'):
            print u['user_id'], u['ecounting_account'], u['info'] if info else ''

