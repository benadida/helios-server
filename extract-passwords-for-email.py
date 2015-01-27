# Copyright 2014 Ben Adida
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# extract voter_id and passwords for a particular email address
# may return many rows, if they all have the same email address
#
# python extract-passwords-for-email.py <election_uuid> <email_address>
#

from django.core.management import setup_environ
import settings, sys, csv

setup_environ(settings)

from helios.models import *

election_uuid = sys.argv[1]
email = sys.argv[2]

csv_output = csv.writer(sys.stdout)

voters = Election.objects.get(uuid=election_uuid).voter_set.filter(voter_email=email)

for voter in voters:
    csv_output.writerow([voter.voter_login_id, voter.voter_password])

