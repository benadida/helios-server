#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module replaces the Django mail implementation with a version that sends
email via the mail API provided by Google App Engine.

Multipart / HTML email is not yet supported.
"""

import logging

from django.core import mail
from django.core.mail import SMTPConnection
from django.conf import settings

from google.appengine.api import mail as gmail


class GoogleSMTPConnection(SMTPConnection):
  def __init__(self, host=None, port=None, username=None, password=None,
               use_tls=None, fail_silently=False):
    self.use_tls = (use_tls is not None) and use_tls or settings.EMAIL_USE_TLS
    self.fail_silently = fail_silently
    self.connection = None

  def open(self):
    self.connection = True

  def close(self):
    pass

  def _send(self, email_message):
    """A helper method that does the actual sending."""
    if not email_message.to:
      return False
    try:
      if (isinstance(email_message,gmail.EmailMessage)):
        e = message
      elif (isinstance(email_message,mail.EmailMessage)):
        e = gmail.EmailMessage(sender=email_message.from_email,
                               to=email_message.to,
                               subject=email_message.subject,
                               body=email_message.body)
        if email_message.extra_headers.get('Reply-To', None):
            e.reply_to = email_message.extra_headers['Reply-To']
        if email_message.bcc:
            e.bcc = list(email_message.bcc)
        #TODO - add support for html messages and attachments...
      e.send()
    except:
      if not self.fail_silently:
          raise
      return False
    return True


def mail_admins(subject, message, fail_silently=False):
    """Sends a message to the admins, as defined by the ADMINS setting."""
    _mail_group(settings.ADMINS, subject, message, fail_silently)


def mail_managers(subject, message, fail_silently=False):
    """Sends a message to the managers, as defined by the MANAGERS setting."""
    _mail_group(settings.MANAGERS, subject, message, fail_silently)


def _mail_group(group, subject, message, fail_silently=False):
    """Sends a message to an administrative group."""
    if group:
      mail.send_mail(settings.EMAIL_SUBJECT_PREFIX + subject, message,
                     settings.SERVER_EMAIL, [a[1] for a in group],
                     fail_silently)
      return
    # If the group had no recipients defined, default to the App Engine admins.
    try:
      gmail.send_mail_to_admins(settings.SERVER_EMAIL,
                                settings.EMAIL_SUBJECT_PREFIX + subject,
                                message)
    except:
      if not fail_silently:
        raise
