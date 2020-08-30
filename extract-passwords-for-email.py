#
# extract voter_id and passwords for a particular email address
# may return many rows, if they all have the same email address
#
# python extract-passwords-for-email.py <election_uuid> <email_address>
#

import sys

import csv
import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from helios.models import Election

election_uuid = sys.argv[1]
email = sys.argv[2]

csv_output = csv.writer(sys.stdout)

voters = Election.objects.get(uuid=election_uuid).voter_set.filter(voter_email=email)

for voter in voters:
    csv_output.writerow([voter.voter_login_id, voter.voter_password])

