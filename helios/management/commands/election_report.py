"""
"""
import datetime
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.timesince import timesince

from helios import utils as helios_utils
from helios.models import *

from zeus import reports

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

try:
  from collections import OrderedDict
except ImportError:
  from django.utils.datastructures import SortedDict as OrderedDict

def json_handler(obj):
  if hasattr(obj, 'isoformat'):
    return obj.isoformat()
  raise TypeError

class Command(BaseCommand):
    args = ''
    help = 'Election report'

    def handle(self, *args, **options):
      elections = Election.objects.filter(uuid__in=args)
      for e in args:

        _reports = OrderedDict()
        _reports['election'] = list(reports.election_report(elections))
        _reports['voters'] = list(reports.election_voters_report(elections))
        _reports['votes'] = list(reports.election_votes_report(elections,
                                                               False))

        json.dump(_reports, sys.stdout, default=json_handler, ensure_ascii=False,
                 indent=4)

