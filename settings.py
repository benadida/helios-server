# -*- coding: utf-8 -*-
import os

# go through environment variables and override them
def get_from_env(var, default):
    if os.environ.has_key(var):
        return os.environ[var]
    else:
        return default

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Grnet user', 'test@grnet.gr'),
)

ELECTION_ADMINS = (
    ('Grnet user', 'tesst@grnet.gr'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'helios'
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Athens'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'el'
LANGUAGES = (('el', 'Greek'),)

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = '/home/zeus/'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = get_from_env('SECRET_KEY', 'replaceme')

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'pagination.middleware.PaginationMiddleware',
)

ROOT_URLCONF = 'urls'

ROOT_PATH = os.path.dirname(__file__)
TEMPLATE_DIRS = (
    ROOT_PATH,
    os.path.join(ROOT_PATH, 'templates')
)

INSTALLED_APPS = (
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'pagination',
    'djcelery',
    'djkombu',
    'south',
    'heliosauth',
    'helios',
    'zeus',
    'server_ui',
)


TEMPLATE_CONTEXT_PROCESSORS = (
  "django.contrib.auth.context_processors.auth",
  "django.core.context_processors.debug",
  "django.core.context_processors.i18n",
  "django.core.context_processors.media",
  "django.core.context_processors.static",
  "django.core.context_processors.request",
  "django.contrib.messages.context_processors.messages")

##
## HELIOS
##

MEDIA_ROOT = MEDIA_ROOT

# a relative path where voter upload files are stored
VOTER_UPLOAD_REL_PATH = "voters/%Y/%m/%d"

# Change your email settings
DEFAULT_FROM_EMAIL = get_from_env('DEFAULT_FROM_EMAIL', 'elections@zeus.minedu.gov.gr')
DEFAULT_FROM_NAME = get_from_env('DEFAULT_FROM_NAME', 'Εκλογές zeus.minedu.gov.gr')
SERVER_EMAIL = '%s <%s>' % (DEFAULT_FROM_NAME, DEFAULT_FROM_EMAIL)

LOGIN_URL = '/auth/'
LOGOUT_ON_CONFIRMATION = False

SITE_DOMAIN = "zeus.minedu.gov.gr"
# The two hosts are here so the main site can be over plain HTTP
# while the voting URLs are served over SSL.
URL_HOST = get_from_env("URL_HOST", "http://%s:8000" % SITE_DOMAIN)

# IMPORTANT: you should not change this setting once you've created
# elections, as your elections' cast_url will then be incorrect.
# SECURE_URL_HOST = "https://localhost:8443"
SECURE_URL_HOST = get_from_env("SECURE_URL_HOST", "http://%s:8000" % SITE_DOMAIN)

# this additional host is used to iframe-isolate the social buttons,
# which usually involve hooking in remote JavaScript, which could be
# a security issue. Plus, if there's a loading issue, it blocks the whole
# page. Not cool.
SOCIALBUTTONS_URL_HOST= get_from_env("SOCIALBUTTONS_URL_HOST", "http://%s:8000" % SITE_DOMAIN)

# election stuff
SITE_TITLE = get_from_env('SITE_TITLE', 'Ηλεκτρονική κάλπη "Ζευς"')

# FOOTER links
FOOTER_LINKS = []
FOOTER_LOGO = False

WELCOME_MESSAGE = get_from_env('WELCOME_MESSAGE', "This is the default message")

HELP_EMAIL_ADDRESS = get_from_env('HELP_EMAIL_ADDRESS', 'help@heliosvoting.org')

AUTH_TEMPLATE_BASE = "server_ui/templates/base.html"
HELIOS_TEMPLATE_BASE = "server_ui/templates/base.html"
HELIOS_ADMIN_ONLY = False
HELIOS_VOTERS_UPLOAD = True
HELIOS_VOTERS_EMAIL = True

# are elections private by default?
HELIOS_PRIVATE_DEFAULT = False

# authentication systems enabled
#AUTH_ENABLED_AUTH_SYSTEMS = ['password','facebook','twitter', 'google', 'yahoo']
AUTH_ENABLED_AUTH_SYSTEMS = ['google']
AUTH_DEFAULT_AUTH_SYSTEM = None

# facebook
FACEBOOK_APP_ID = ''
FACEBOOK_API_KEY = ''
FACEBOOK_API_SECRET = ''

# twitter
TWITTER_API_KEY = ''
TWITTER_API_SECRET = ''
TWITTER_USER_TO_FOLLOW = 'heliosvoting'
TWITTER_REASON_TO_FOLLOW = "we can direct-message you when the result has been computed in an election in which you participated"

# the token for Helios to do direct messaging
TWITTER_DM_TOKEN = {"oauth_token": "", "oauth_token_secret": "", "user_id": "", "screen_name": ""}

# LinkedIn
LINKEDIN_API_KEY = ''
LINKEDIN_API_SECRET = ''

# email server
EMAIL_HOST = get_from_env('EMAIL_HOST', 'localhost')
EMAIL_PORT = 2525
EMAIL_HOST_USER = get_from_env('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = get_from_env('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = False

# set up logging
import logging
logging.basicConfig(
    level = logging.INFO if DEBUG else logging.INFO,
    format = '%(asctime)s %(levelname)s %(message)s'
)

# set up django-celery
import djcelery
djcelery.setup_loader()
BROKER_BACKEND = "djkombu.transport.DatabaseTransport"
CELERY_RESULT_DBURI = DATABASES['default']

# for testing
CELERY_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True


BOOTH_STATIC_PATH = ROOT_PATH + '/heliosbooth/'
VERIFIER_STATIC_PATH = ROOT_PATH + '/heliosverifier/'

ECOUNTING_LOGIN_URL = "https://x.x.x.x/checkuser.php"
ECOUNTING_POST_URL = "https://x.x.x.x/newelection.php"
ECOUNTING_CHECK_URL = "https://x.x.x.x/newelection.php"
ECOUNTING_SECRET = "xxxxx"

HELIOS_VOTER_EMAIL_RATE = '30/m'

ZEUS_RESULTS_PATH = os.path.join('/', 'usr', 'share', 'zeus')
ZEUS_PROOFS_PATH = os.path.join('/', 'usr', 'share', 'zeus_proofs')
ZEUS_MIXES_PATH = 'zeus_mixes'
ZEUS_ELECTION_FORCE_VOTING_END = True
ZEUS_CELERY_TEMPDIR = os.path.join('/', 'var', 'run', 'zeus-celery')

CANDIDATES_CHANGE_TIME_MARGIN = 1

COLLATION_LOCALE = 'el_GR.UTF-8'

MIX_PART_SIZE = 104857600


USE_X_SENDFILE = False

# useful trick for custom settings
try:
    from local_settings import *
except ImportError:
    pass
