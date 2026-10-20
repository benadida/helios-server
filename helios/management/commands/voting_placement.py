"""Read-only deployment diagnostic: print regions and probe time, never a URL."""
import json
import os
import re
import time

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Report container location, database region and a read-only probe time.'

    def handle(self, *args, **options):
        host = connection.settings_dict.get('HOST', '')
        match = re.search(r'\b((?:us|eu|ap|ca|sa|me|af|il)-(?:east|west|central|south|north|southeast|northeast)-\d)\b', host)
        started = time.monotonic()
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        location = re.sub(r'[^A-Za-z0-9 _-]', '', os.environ.get('CLOUDFLARE_LOCATION', 'unknown'))[:80]
        self.stdout.write(json.dumps({'container_location': location,
            'database_region': match[1] if match else 'unknown',
            'transaction_pooler': '-pooler' in host,
            'database_probe_ms': round((time.monotonic()-started)*1000, 1)}))
