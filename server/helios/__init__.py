from django.conf import settings

from helios.celery_app import app as celery_app

__all__ = ('celery_app', 'TEMPLATE_BASE', 'ADMIN_ONLY', 'VOTERS_UPLOAD', 'VOTERS_EMAIL',)

TEMPLATE_BASE = settings.HELIOS_TEMPLATE_BASE or "helios/templates/base.html"

# a setting to ensure that only admins can create an election
ADMIN_ONLY = settings.HELIOS_ADMIN_ONLY

# allow upload of voters via CSV?
VOTERS_UPLOAD = settings.HELIOS_VOTERS_UPLOAD

# allow emailing of voters?
VOTERS_EMAIL = settings.HELIOS_VOTERS_EMAIL
