
AUTH_SYSTEMS = {}

import twitter, password, cas, facebook, google, yahoo, linkedin, clever
AUTH_SYSTEMS['twitter'] = twitter
AUTH_SYSTEMS['linkedin'] = linkedin
AUTH_SYSTEMS['password'] = password
AUTH_SYSTEMS['cas'] = cas
AUTH_SYSTEMS['facebook'] = facebook
AUTH_SYSTEMS['google'] = google
AUTH_SYSTEMS['yahoo'] = yahoo
AUTH_SYSTEMS['clever'] = clever

# not ready
#import live
#AUTH_SYSTEMS['live'] = live

def can_check_constraint(auth_system):
    return hasattr(AUTH_SYSTEMS[auth_system], 'check_constraint')

def can_list_categories(auth_system):
    return hasattr(AUTH_SYSTEMS[auth_system], 'list_categories')
