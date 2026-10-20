"""LISTEN is a latency hint. The durable queue is always probed on timeout.

Use a dedicated session connection (never a transaction-pooler URL). Losing a
connection/notification cannot lose work: the worker keeps its polling fallback.
"""
import logging
import select
import time

from django.db import connections
from psycopg2 import Error as DriverError

logger = logging.getLogger(__name__)


class VerificationWakeup:
    def __init__(self):
        self.listener = None
        self.retry_at = 0

    def connect(self):
        if self.listener is not None or time.monotonic() < self.retry_at:
            return
        listener = connections['default'].copy(alias='verification_listener')
        listener.settings_dict['OPTIONS'] = {
            **listener.settings_dict.get('OPTIONS', {}), 'connect_timeout': 5}
        try:
            listener.ensure_connection()
            listener.set_autocommit(True)
            with listener.cursor() as cursor:
                cursor.execute('LISTEN helios_vote_verification')
            self.listener = listener
        except Exception:
            listener.close()
            self.retry_at = time.monotonic() + 60
            logger.warning('Verification wake connection unavailable; polling retained.')

    def wait(self, timeout):
        if self.listener is None:
            time.sleep(timeout)
            return
        try:
            raw = self.listener.connection
            # Drain queued hints before sleeping, including hints that arrived
            # between the last queue probe and this call.
            raw.poll()
            if not raw.notifies:
                select.select([raw], [], [], timeout)
                raw.poll()
            raw.notifies.clear()
        except (DriverError, OSError, ValueError):
            self.close()
            self.retry_at = time.monotonic() + 60
            logger.warning('Verification wake connection lost; polling retained.')
            time.sleep(timeout)

    def close(self):
        if self.listener is not None:
            self.listener.close()
            self.listener = None
