from django.conf import settings
from . import password, linkedin, cas, facebook, google, yahoo, clever, github, ldapauth, gitlab

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

# not ready
#import live
#AUTH_SYSTEMS['live'] = live

def can_check_constraint(auth_system):
    return auth_system in AUTH_SYSTEMS and hasattr(AUTH_SYSTEMS[auth_system], 'check_constraint')

def can_list_categories(auth_system):
    return auth_system in AUTH_SYSTEMS and hasattr(AUTH_SYSTEMS[auth_system], 'list_categories')
