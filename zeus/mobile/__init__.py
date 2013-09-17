from django.conf import settings

from zeus.mobile import locotel


def get_client():
    return locotel.Loco(settings.ZEUS_SMS_API_SENDER,
                        settings.ZEUS_SMS_API_USERNAME,
                        settings.ZEUS_SMS_API_PASSWORD)
