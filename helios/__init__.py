from django.conf import settings
from django.core.urlresolvers import reverse

TEMPLATE_BASE = settings.HELIOS_TEMPLATE_BASE or "helios/templates/base.html"
TEMPLATE_BASENONAV = settings.HELIOS_TEMPLATE_BASENONAV or "helios/templates/base.html"

# allow upload of voters via CSV?
VOTERS_UPLOAD = settings.HELIOS_VOTERS_UPLOAD

# allow emailing of voters?
VOTERS_EMAIL = settings.HELIOS_VOTERS_EMAIL


