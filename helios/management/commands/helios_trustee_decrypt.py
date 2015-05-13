"""
decrypt elections where Helios is trustee

DEPRECATED

Ben Adida
ben@adida.net
2010-05-22
"""

from django.core.management.base import BaseCommand, CommandError
import csv, datetime

from helios import utils as helios_utils

from helios.models import *

class Command(BaseCommand):
    args = ''
    help = 'decrypt elections where helios is the trustee'
    
    def handle(self, *args, **options):
        # query for elections where decryption is ready to go and Helios is the trustee
        active_helios_trustees = Trustee.objects.exclude(secret_key = None).exclude(election__encrypted_tally = None).filter(decryption_factors = None)

        # for each one, do the decryption
        for t in active_helios_trustees:
            t.election.helios_trustee_decrypt()
