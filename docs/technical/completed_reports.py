#!/usr/bin/python
import os
import sys

sys.path.append("/srv/zeus-server/")

from django.core.management import setup_environ
import settings
setup_environ(settings)

from helios.models import *
from zeus import reports

def election_reports(election):
    data = {}
    data['election'] = list(reports.election_report([election], True, True))[0]
    data['votes'] = list(reports.election_votes_report([election], True, True))[0]
    data['voters'] = list(reports.election_voters_report([election]))[0]
    data['results'] = list(reports.election_results_report([election]))[0]
    return data

import json

elections = Election.objects.filter(is_completed=True)

DATA = {}
for election in elections:
    DATA[election.uuid] = election_reports(election)

def handler(obj):
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    raise TypeError

print json.dumps(DATA, default=handler, ensure_ascii=True)

