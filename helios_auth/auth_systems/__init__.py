from django.conf import settings
from . import password, linkedin, cas, facebook, google, yahoo, clever, github, ldapauth, gitlab

# Import devlogin only in debug mode
if settings.DEBUG:
    from . import devlogin

AUTH_SYSTEMS = {}

AUTH_SYSTEMS['password'] = password
AUTH_SYSTEMS['linkedin'] = linkedin
AUTH_SYSTEMS['cas'] = cas
AUTH_SYSTEMS['facebook'] = facebook
AUTH_SYSTEMS['google'] = google
AUTH_SYSTEMS['yahoo'] = yahoo
AUTH_SYSTEMS['clever'] = clever
AUTH_SYSTEMS['github'] = github
AUTH_SYSTEMS['ldap'] = ldapauth
AUTH_SYSTEMS['gitlab'] = gitlab

# Add devlogin only in debug mode
if settings.DEBUG:
    AUTH_SYSTEMS['devlogin'] = devlogin

# not ready
#import live
#AUTH_SYSTEMS['live'] = live

def can_check_constraint(auth_system):
    return auth_system in AUTH_SYSTEMS and hasattr(AUTH_SYSTEMS[auth_system], 'check_constraint')

def can_list_categories(auth_system):
    return auth_system in AUTH_SYSTEMS and hasattr(AUTH_SYSTEMS[auth_system], 'list_categories')

def uses_case_insensitive_user_id(auth_system):
    """
    Check if an auth system uses case-insensitive user IDs.
    Auth systems can opt in by setting CASE_INSENSITIVE_USER_ID = True.
    """
    return auth_system in AUTH_SYSTEMS and getattr(AUTH_SYSTEMS[auth_system], 'CASE_INSENSITIVE_USER_ID', False)
