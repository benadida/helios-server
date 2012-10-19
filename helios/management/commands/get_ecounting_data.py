from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from helios import utils as helios_utils
from helios.models import *
from heliosauth.models import *
import json
import sys

class Command(BaseCommand):
    args = ''
    help = 'Get JSON data submitted to e-counting'

    def handle(self, *args, **options):
        reload(sys)
        sys.setdefaultencoding('utf-8')
        e = Election.objects.get(uuid=args[0])
        d = e.ecounting_dict()
        sys.stdout.write(json.dumps(d, indent=2, ensure_ascii=0, encoding='utf-8'))

