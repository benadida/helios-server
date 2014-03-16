import os
import json

# Go through environment variables and override them
def get_from_env(var, default):
    if os.environ.has_key(var):
        return os.environ[var]
    else:
        return default

DEBUG = (get_from_env('DEBUG', '1') == '1')
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Pieter Maene', 'p.maene@gmail.com'),
)

MANAGERS = ADMINS

# Is this the master Helios web site?
MASTER_HELIOS = (get_from_env('MASTER_HELIOS', '0') == '1')

# Show ability to log in? For example, if the site is mostly used by voters.
# If turned off, the admin will need to know to go to /auth/login manually.
SHOW_LOGIN_OPTIONS = (get_from_env('SHOW_LOGIN_OPTIONS', '1') == '1')

# Sometimes, when the site is not that social, it's not helpful
# to display who created the election.
SHOW_USER_INFO = (get_from_env('SHOW_USER_INFO', '1') == '1')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'helios',
        'HOST': '127.0.0.1'
    }
}

SOUTH_DATABASE_ADAPTERS = {'default': 'south.db.postgresql_psycopg2'}

# Override if we have an environment variable
if get_from_env('DATABASE_URL', None):
    import dj_database_url
    DATABASES['default'] = dj_database_url.config()
    DATABASES['default']['ENGINE'] = 'dbpool.db.backends.postgresql_psycopg2'
    DATABASES['default']['OPTIONS'] = {'MAX_CONNS': 1}

# Local time zone for this installation.
#
# Choices can be found here on
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name,
# lthough not all choices may be available on all operating systems.
#
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Brussels'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html.
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
MEDIA_URL = ''

# URL prefix for admin media such as CSS, JavaScript and images. Make sure to use a
# trailing slash.
STATIC_URL = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = get_from_env('SECRET_KEY', '111111111111111111111111111')

# Secure stuff
if (get_from_env('SSL', '0') == '1'):
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True

    # Tuned for Heroku
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SESSION_COOKIE_HTTPONLY = True

# One week HSTS seems like a good balance for MITM prevention
if (get_from_env('HSTS', '0') == '1'):
    SECURE_HSTS_SECONDS = 3600 * 24 * 7
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader'
)

MIDDLEWARE_CLASSES = (
    # Secure a bunch of things
    'djangosecure.middleware.SecurityMiddleware',

    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware'
)

ROOT_URLCONF = 'urls'

ROOT_PATH = os.path.dirname(__file__)
TEMPLATE_DIRS = (
    ROOT_PATH,
    os.path.join(ROOT_PATH, 'templates')
)

INSTALLED_APPS = (
    'djangosecure',
    'django.contrib.sessions',
    'django.contrib.sites',

    # Needed for queues
    'djcelery',
    'kombu.transport.django',

    # Needed for schema migration
    'south',

    # Foundation forms
    'foundationform',

    # Helios
    'helios_auth',
    'helios',
    'server_ui',
    'bulletin_board',
)

##
# Helios
##

MEDIA_ROOT = ROOT_PATH + 'media/'

# Relative path where voter upload files are stored
VOTER_UPLOAD_REL_PATH = 'voters/%Y/%m/%d'

# Change your email settings
DEFAULT_FROM_EMAIL = get_from_env(
    'DEFAULT_FROM_EMAIL', 'helios@heliosvoting.org')
DEFAULT_FROM_NAME = get_from_env('DEFAULT_FROM_NAME', 'Helios')
SERVER_EMAIL = '%s <%s>' % (DEFAULT_FROM_NAME, DEFAULT_FROM_EMAIL)

LOGIN_URL = '/helios_auth/'
LOGOUT_ON_CONFIRMATION = True

# The two hosts are here so the main site can be over plain HTTP
# while the voting URLs are served over SSL.
URL_HOST = get_from_env('URL_HOST', 'http://localhost:8000')

# IMPORTANT
# You should not change this setting once you've created
# elections, as your elections' cast_url will then be incorrect.
SECURE_URL_HOST = get_from_env('SECURE_URL_HOST', 'http://localhost:8000')

# This additional host is used to iframe-isolate the social buttons,
# which usually involve hooking in remote JavaScript, which could be
# a security issue. Plus, if there's a loading issue, it blocks the whole
# page. Not cool.
SOCIALBUTTONS_URL_HOST = get_from_env(
    'SOCIALBUTTONS_URL_HOST', 'http://localhost:8000')

SITE_TITLE = get_from_env('SITE_TITLE', 'Helios Voting')
MAIN_LOGO_URL = get_from_env('MAIN_LOGO_URL', '/static/logo.png')
ALLOW_ELECTION_INFO_URL = (get_from_env('ALLOW_ELECTION_INFO_URL', '0') == '1')

# Footer links
FOOTER_LINKS = json.loads(get_from_env('FOOTER_LINKS', '[]'))
FOOTER_LOGO_URL = get_from_env('FOOTER_LOGO_URL', None)

WELCOME_MESSAGE = get_from_env(
    'WELCOME_MESSAGE', 'This is the default message.')

HELP_EMAIL_ADDRESS = get_from_env(
    'HELP_EMAIL_ADDRESS', 'help@heliosvoting.org')

AUTH_TEMPLATE_BASE = 'server_ui/templates/base.html'
HELIOS_TEMPLATE_BASE = 'server_ui/templates/base.html'
HELIOS_ADMIN_ONLY = False
HELIOS_VOTERS_UPLOAD = True
HELIOS_VOTERS_EMAIL = True

# Are elections private by default?
HELIOS_PRIVATE_DEFAULT = False

# The authentication systems that should be enabled.
#AUTH_ENABLED_AUTH_SYSTEMS = ['password','facebook','twitter', 'google', 'yahoo']
AUTH_ENABLED_AUTH_SYSTEMS = get_from_env(
    'AUTH_ENABLED_AUTH_SYSTEMS', 'google').split(',')
AUTH_DEFAULT_AUTH_SYSTEM = get_from_env('AUTH_DEFAULT_AUTH_SYSTEM', None)

# Facebook
FACEBOOK_APP_ID = get_from_env('FACEBOOK_APP_ID', '')
FACEBOOK_API_KEY = get_from_env('FACEBOOK_API_KEY', '')
FACEBOOK_API_SECRET = get_from_env('FACEBOOK_API_SECRET', '')

# Twitter
TWITTER_API_KEY = ''
TWITTER_API_SECRET = ''
TWITTER_USER_TO_FOLLOW = 'heliosvoting'
TWITTER_REASON_TO_FOLLOW = 'We can DM you when the result has been computed in an election in which you participated.'

# The token for Helios to do direct messaging.
TWITTER_DM_TOKEN = {
    'oauth_token': '', 'oauth_token_secret': '', 'user_id': '', 'screen_name': ''}

# LinkedIn
LINKEDIN_API_KEY = ''
LINKEDIN_API_SECRET = ''

# CAS
CAS_USERNAME = get_from_env('CAS_USERNAME', '')
CAS_PASSWORD = get_from_env('CAS_PASSWORD', '')
CAS_ELIGIBILITY_URL = get_from_env('CAS_ELIGIBILITY_URL', '')
CAS_ELIGIBILITY_REALM = get_from_env('CAS_ELIGIBILITY_REALM', '')

# Email
EMAIL_HOST = get_from_env('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(get_from_env('EMAIL_PORT', '2525'))
EMAIL_HOST_USER = get_from_env('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = get_from_env('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = (get_from_env('EMAIL_USE_TLS', '0') == '1')

# Logging
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s'
)

# django-celery
BROKER_URL = 'django://'
CELERY_RESULT_DBURI = DATABASES['default']
import djcelery
djcelery.setup_loader()

# Testing
# This effectively does CELERY_ALWAYS_EAGER = True
TEST_RUNNER = 'djcelery.contrib.test_runner.CeleryTestSuiteRunner'
