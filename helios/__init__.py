from django.conf import settings
from django.urls import reverse
import os


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

TEMPLATE_BASE = settings.HELIOS_TEMPLATE_BASE or "helios/templates/base.html"

# a setting to ensure that only admins can create an election
ADMIN_ONLY = settings.HELIOS_ADMIN_ONLY

# allow upload of voters via CSV?
VOTERS_UPLOAD = settings.HELIOS_VOTERS_UPLOAD

# allow emailing of voters?
VOTERS_EMAIL = settings.HELIOS_VOTERS_EMAIL

# Celery
# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app

__all__ = ('celery_app',)
