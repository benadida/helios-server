"""
"""
from django.core.management.base import BaseCommand

from helios.models import *
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

class Command(BaseCommand):
    args = ''
    help = 'List the voters'

    def handle(self, *args, **options):
        if args:
	    election = Election.objects.get(uuid=args[0])
            voters = Voter.objects.filter(election=election)
        else:
            voters = Voter.objects.all()

        for v in voters:
            print v.voter_email, v.voter_surname, v.voter_name, v.voter_fathername

