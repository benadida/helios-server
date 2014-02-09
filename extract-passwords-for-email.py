#
# extract voter_id and passwords for a particular email address
# may return many rows, if they all have the same email address
#
# python extract-passwords-for-email.py <email_address>
#

from django.core.management import setup_environ
import settings, sys

setup_environ(settings)

email = sys.argv[1]

from helios.models import *
print email
print str(Election.objects.count())
