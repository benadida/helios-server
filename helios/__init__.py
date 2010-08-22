
from django.conf import settings

TEMPLATE_BASE = settings.HELIOS_TEMPLATE_BASE or "helios/templates/base.html"

# a setting to ensure that only admins can create an election
ADMIN_ONLY = settings.HELIOS_ADMIN_ONLY

# allow upload of voters via CSV?
VOTERS_UPLOAD = settings.HELIOS_VOTERS_UPLOAD

# allow emailing of voters?
VOTERS_EMAIL = settings.HELIOS_VOTERS_EMAIL

from django.core.urlresolvers import reverse

# get the short path for the URL
def get_election_url(election):
  from views import election_shortcut
  return settings.URL_HOST + reverse(election_shortcut, args=[election.short_name])
