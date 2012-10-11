from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from helios import utils as helios_utils
from helios.models import *
from heliosauth.models import *

class Command(BaseCommand):
    args = ''
    help = 'Show the voter login url'

    def handle(self, *args, **options):
        Election.objects.all().delete()
        User.objects.filter(superadmin_p=False).delete()
