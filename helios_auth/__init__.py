
from django.conf import settings

TEMPLATE_BASE = settings.AUTH_TEMPLATE_BASE or "helios_auth/templates/base.html"

# enabled auth systems
from . import auth_systems
ENABLED_AUTH_SYSTEMS = settings.AUTH_ENABLED_SYSTEMS or list(auth_systems.AUTH_SYSTEMS.keys())
DEFAULT_AUTH_SYSTEM = settings.AUTH_DEFAULT_SYSTEM or None

