"""
Text messages, sent with the backend named by settings.SMS_BACKEND:
'twilio' sends them, 'console' logs them, 'locmem' keeps them in outbox (tests)
"""

import logging

import requests
from django.conf import settings

TWILIO_MESSAGES_URL = "https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json"

outbox = []

def send_sms(to, body):
  if settings.SMS_BACKEND == 'twilio':
    response = requests.post(TWILIO_MESSAGES_URL % settings.TWILIO_ACCOUNT_SID,
                             auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
                             data={'To': to, 'From': settings.TWILIO_FROM_NUMBER, 'Body': body},
                             timeout=10)
    response.raise_for_status()
  elif settings.SMS_BACKEND == 'locmem':
    outbox.append({'to': to, 'body': body})
  else:
    logging.getLogger(__name__).info("text message to %s:\n%s", to, body)
