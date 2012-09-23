"""
Extend default helios settings adjusted for phoebus election system.
"""

from settings import *

# we only need password authentication system (no facebook/google/openid etc.)
ENABLED_AUTH_SYSTEMS = ['password']


try:
    from local_settings import *
except ImportError:
    pass
