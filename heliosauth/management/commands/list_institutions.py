from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from heliosauth.models import *
from zeus.models import *

import pprint


institution_row = "%-3d %-70s %-2d"
institution_row_header = "%-3s %-70s %-2s"

class Command(BaseCommand):
    args = ''
    help = 'List institutions'


    def handle(self, *args, **options):
        info = False
        if len(args) > 0 and args[0] == "1":
            info = True

        print institution_row_header % ('ID', 'NAME', 'USERS')
        for inst in Institution.objects.all():
            users_count = inst.user_set.count()
            print institution_row % (inst.pk, inst.name, users_count)


