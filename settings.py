
# a massive hack to see if we're testing, in which case we use different settings
import sys

import json
import os

TESTING = 'test' in sys.argv

# go through environment variables and override them
def get_from_env(var, default):
    if not TESTING and var in os.environ:
        return os.environ[var]
    else:
        return default

DEBUG = (get_from_env('DEBUG', '1') == '1')

# add admins of the form: 
#    ('Ben Adida', 'ben@adida.net'),
# if you want to be emailed about errors.
ADMINS = (
)

MANAGERS = ADMINS

# is this the master Helios web site?
MASTER_HELIOS = (get_from_env('MASTER_HELIOS', '0') == '1')

# show ability to log in? (for example, if the site is mostly used by voters)
# if turned off, the admin will need to know to go to /auth/login manually
SHOW_LOGIN_OPTIONS = (get_from_env('SHOW_LOGIN_OPTIONS', '1') == '1')

# sometimes, when the site is not that social, it's not helpful
# to display who created the election
SHOW_USER_INFO = (get_from_env('SHOW_USER_INFO', '1') == '1')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'helios',
        'CONN_MAX_AGE': 600,
    },
}

# override if we have an env variable
if get_from_env('DATABASE_URL', None):
    import dj_database_url
    DATABASES['default'] = dj_database_url.config(conn_max_age=600, ssl_require=True)
    DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql_psycopg2'

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Los_Angeles'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
STATIC_URL = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = get_from_env('SECRET_KEY', 'replaceme')

# If debug is set to false and ALLOWED_HOSTS is not declared, django raises  "CommandError: You must set settings.ALLOWED_HOSTS if DEBUG is False."
# If in production, you got a bad request (400) error
#More info: https://docs.djangoproject.com/en/1.7/ref/settings/#allowed-hosts (same for 1.6)

ALLOWED_HOSTS = get_from_env('ALLOWED_HOSTS', 'localhost').split(",")

# Secure Stuff
if get_from_env('SSL', '0') == '1':
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True

    # tuned for Heroku
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_HTTPONLY = True

# let's go with one year because that's the way to do it now
STS = False
if get_from_env('HSTS', '0') == '1':
    STS = True
    # we're using our own custom middleware now
    # SECURE_HSTS_SECONDS = 31536000
    # not doing subdomains for now cause that is not likely to be necessary and can screw things up.
    # SECURE_HSTS_INCLUDE_SUBDOMAINS = True

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

SILENCED_SYSTEM_CHECKS = ['urls.W002']

MIDDLEWARE = [
    # secure a bunch of things
    'django.middleware.security.SecurityMiddleware',
    'helios.security.HSTSMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',

    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
]

ROOT_URLCONF = 'urls'

ROOT_PATH = os.path.dirname(__file__)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'DIRS': [
            ROOT_PATH,
            os.path.join(ROOT_PATH, 'templates'),
            # os.path.join(ROOT_PATH, 'helios/templates'),  # covered by APP_DIRS:True
            # os.path.join(ROOT_PATH, 'helios_auth/templates'),  # covered by APP_DIRS:True
            # os.path.join(ROOT_PATH, 'server_ui/templates'),  # covered by APP_DIRS:True
        ],
        'OPTIONS': {
            'debug': DEBUG
        }
    },
]

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    ## HELIOS stuff
    'helios_auth',
    'helios',
    'server_ui',
)

##
## HELIOS
##


MEDIA_ROOT = ROOT_PATH + "media/"

# a relative path where voter upload files are stored
VOTER_UPLOAD_REL_PATH = "voters/%Y/%m/%d"


# Change your email settings
DEFAULT_FROM_EMAIL = get_from_env('DEFAULT_FROM_EMAIL', 'ben@adida.net')
DEFAULT_FROM_NAME = get_from_env('DEFAULT_FROM_NAME', 'Ben for Helios')
SERVER_EMAIL = '%s <%s>' % (DEFAULT_FROM_NAME, DEFAULT_FROM_EMAIL)

LOGIN_URL = '/auth/'
LOGOUT_ON_CONFIRMATION = True

# The two hosts are here so the main site can be over plain HTTP
# while the voting URLs are served over SSL.
URL_HOST = get_from_env("URL_HOST", "http://localhost:8000").rstrip("/")

# IMPORTANT: you should not change this setting once you've created
# elections, as your elections' cast_url will then be incorrect.
# SECURE_URL_HOST = "https://localhost:8443"
SECURE_URL_HOST = get_from_env("SECURE_URL_HOST", URL_HOST).rstrip("/")

# election stuff
SITE_TITLE = get_from_env('SITE_TITLE', 'Helios Voting')
MAIN_LOGO_URL = get_from_env('MAIN_LOGO_URL', '/static/logo.png')
ALLOW_ELECTION_INFO_URL = (get_from_env('ALLOW_ELECTION_INFO_URL', '0') == '1')

# FOOTER links
FOOTER_LINKS = json.loads(get_from_env('FOOTER_LINKS', '[]'))
FOOTER_LOGO_URL = get_from_env('FOOTER_LOGO_URL', None)

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
# AUTH_ENABLED_SYSTEMS = ['password','facebook','twitter', 'google', 'yahoo']
AUTH_ENABLED_SYSTEMS = get_from_env('AUTH_ENABLED_SYSTEMS',
                                    get_from_env('AUTH_ENABLED_AUTH_SYSTEMS', 'password,google,facebook')
                                    ).split(",")
AUTH_DEFAULT_SYSTEM = get_from_env('AUTH_DEFAULT_SYSTEM', get_from_env('AUTH_DEFAULT_AUTH_SYSTEM', None))

# google
GOOGLE_CLIENT_ID = get_from_env('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = get_from_env('GOOGLE_CLIENT_SECRET', '')

# facebook
FACEBOOK_APP_ID = get_from_env('FACEBOOK_APP_ID','')
FACEBOOK_API_KEY = get_from_env('FACEBOOK_API_KEY','')
FACEBOOK_API_SECRET = get_from_env('FACEBOOK_API_SECRET','')

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

# CAS (for universities)
CAS_USERNAME = get_from_env('CAS_USERNAME', "")
CAS_PASSWORD = get_from_env('CAS_PASSWORD', "")
CAS_ELIGIBILITY_URL = get_from_env('CAS_ELIGIBILITY_URL', "")
CAS_ELIGIBILITY_REALM = get_from_env('CAS_ELIGIBILITY_REALM', "")

# Clever
CLEVER_CLIENT_ID = get_from_env('CLEVER_CLIENT_ID', "")
CLEVER_CLIENT_SECRET = get_from_env('CLEVER_CLIENT_SECRET', "")

# email server
EMAIL_HOST = get_from_env('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(get_from_env('EMAIL_PORT', "2525"))
EMAIL_HOST_USER = get_from_env('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = get_from_env('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = (get_from_env('EMAIL_USE_TLS', '0') == '1')

# to use AWS Simple Email Service
# in which case environment should contain
# AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
if get_from_env('EMAIL_USE_AWS', '0') == '1':
    EMAIL_BACKEND = 'django_ses.SESBackend'

# set up logging
import logging

logging.basicConfig(
    level=logging.DEBUG if TESTING else logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

# set up celery
CELERY_BROKER_URL = get_from_env('CELERY_BROKER_URL', 'amqp://localhost')
if TESTING:
    CELERY_TASK_ALWAYS_EAGER = True
#database_url = DATABASES['default']

# Rollbar Error Logging
ROLLBAR_ACCESS_TOKEN = get_from_env('ROLLBAR_ACCESS_TOKEN', None)
if ROLLBAR_ACCESS_TOKEN:
  print("setting up rollbar")
  MIDDLEWARE += ['rollbar.contrib.django.middleware.RollbarNotifierMiddleware',]
  ROLLBAR = {
    'access_token': ROLLBAR_ACCESS_TOKEN,
    'environment': 'development' if DEBUG else 'production',  
  }
