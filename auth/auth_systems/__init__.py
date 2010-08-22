
AUTH_SYSTEMS = {}

import twitter, password, cas, facebook, google, yahoo
AUTH_SYSTEMS['twitter'] = twitter
AUTH_SYSTEMS['password'] = password
AUTH_SYSTEMS['cas'] = cas
AUTH_SYSTEMS['facebook'] = facebook
AUTH_SYSTEMS['google'] = google
AUTH_SYSTEMS['yahoo'] = yahoo

# not ready
#import live
#AUTH_SYSTEMS['live'] = live
