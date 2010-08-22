
from django.conf import settings

TEMPLATE_BASE = settings.AUTH_TEMPLATE_BASE or "auth/templates/base.html"

# enabled auth systems
import auth_systems
ENABLED_AUTH_SYSTEMS = settings.AUTH_ENABLED_AUTH_SYSTEMS or auth_systems.AUTH_SYSTEMS.keys()
DEFAULT_AUTH_SYSTEM = settings.AUTH_DEFAULT_AUTH_SYSTEM or None

