import logging

from collections import defaultdict
from django.conf import settings

from zeus.mobile import locotel

logger = logging.getLogger(__name__)

_default_credentials = {
    'sender': settings.ZEUS_SMS_API_SENDER,
    'username': settings.ZEUS_SMS_API_USERNAME,
    'password': settings.ZEUS_SMS_API_PASSWORD,
}
CREDENTIALS_DICT = defaultdict(lambda: _default_credentials)

ELECTIONS_CREDENTIALS_MAP = getattr(settings, 'ZEUS_SMS_API_CREDENTIALS', {})
CREDENTIALS_DICT.update(ELECTIONS_CREDENTIALS_MAP)

def get_client(election_uuid=None):
    credentials = CREDENTIALS_DICT[election_uuid]
    logger.info("Using sms api credentials for election %r: %r" % (
        election_uuid,
        {
            'username': credentials['username'],
            'sender': credentials['sender']
        }
    ))
    return locotel.Loco(credentials['sender'], credentials['username'],
                        credentials['password'])
