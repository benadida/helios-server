from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from heliosauth.models import *

import pprint

user_row = "%-3d %-15s %-20s %-60s %-10s %-2d"
user_row_header = user_row.replace("d", "s")

class Command(BaseCommand):
    args = ''
    help = 'List users'


    def handle(self, *args, **options):
        info = False

        print user_row_header % ('ID', 'USERNAME', 'NAME', 'INSTITUTION',
                                   'ECOUNTING', 'ELECTIONS')
        for user in User.objects.all():
            elections_count = user.elections.count()
            print user_row % (user.pk, user.user_id, user.name,
                              '%-2d - %s' % (user.institution.pk, user.institution.name),
                              str(user.ecounting_account),
                              elections_count)

