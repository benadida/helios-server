from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from helios import utils as helios_utils
from helios.models import *
from heliosauth.models import *

class Command(BaseCommand):
    args = ''
    help = 'List elections'

    def handle(self, *args, **options):
        for e in Election.objects.all():
            print e.uuid, e.name, '--', e.institution.name
