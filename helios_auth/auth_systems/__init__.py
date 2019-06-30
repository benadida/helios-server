from django.conf import settings

_enabled = settings.AUTH_ENABLED_AUTH_SYSTEMS or None
def _is_enabled(system):
    return _enabled is not None or system in _enabled

AUTH_SYSTEMS = {}

if _is_enabled('twitter'):
    from . import twitter
    AUTH_SYSTEMS['twitter'] = twitter

if _is_enabled('linkedin'):
    from . import linkedin
    AUTH_SYSTEMS['linkedin'] = linkedin

if _is_enabled('password'):
    from . import password
    AUTH_SYSTEMS['password'] = password

if _is_enabled('cas'):
    from . import cas
    AUTH_SYSTEMS['cas'] = cas

if _is_enabled('facebook'):
    from . import facebook
    AUTH_SYSTEMS['facebook'] = facebook

if _is_enabled('google'):
    from . import google
    AUTH_SYSTEMS['google'] = google

if _is_enabled('yahoo'):
    from . import yahoo
    AUTH_SYSTEMS['yahoo'] = yahoo

if _is_enabled('clever'):
    from . import clever
    AUTH_SYSTEMS['clever'] = clever

# not ready
#import live
#AUTH_SYSTEMS['live'] = live

def can_check_constraint(auth_system):
    return hasattr(AUTH_SYSTEMS[auth_system], 'check_constraint')

def can_list_categories(auth_system):
    return hasattr(AUTH_SYSTEMS[auth_system], 'list_categories')
