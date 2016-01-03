from django.conf import settings
# enabled auth systems
import auth_systems

TEMPLATE_BASE = settings.AUTH_TEMPLATE_BASE or "helios_auth/templates/base.html"

ENABLED_AUTH_SYSTEMS = settings.AUTH_ENABLED_AUTH_SYSTEMS or auth_systems.AUTH_SYSTEMS.keys()
DEFAULT_AUTH_SYSTEM = settings.AUTH_DEFAULT_AUTH_SYSTEM or None
