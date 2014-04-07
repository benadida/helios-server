
from django.conf import settings
from django.core.urlresolvers import reverse
from helios.views import election_shortcut

TEMPLATE_BASE = settings.HELIOS_TEMPLATE_BASE or "helios/templates/base.html"

# allow upload of voters via CSV?
VOTERS_UPLOAD = settings.HELIOS_VOTERS_UPLOAD

# allow emailing of voters?
VOTERS_EMAIL = settings.HELIOS_VOTERS_EMAIL


