# -*- coding: utf-8 -*-
import ldap
import os, json

from django.utils.translation import ugettext_lazy as _

from django_auth_ldap.config import LDAPSearch, GroupOfNamesType
# a massive hack to see if we're testing, in which case we use different settings
import sys
TESTING = 'test' in sys.argv

# go through environment variables and override them
def get_from_env(var, default):
    if not TESTING and os.environ.has_key(var):
        return os.environ[var]
    else:
        return default

DEBUG = (get_from_env('DEBUG', '1') == '1')
TEMPLATE_DEBUG = DEBUG

#If the Host header (or X-Forwarded-Host if USE_X_FORWARDED_HOST is enabled) does not match any value in this list, the django.http.HttpRequest.get_host() method will raise SuspiciousOperation.
#When DEBUG is True or when running tests, host validation is disabled; any host will be accepted. Thus it’s usually only necessary to set it in production.
#This validation only applies via get_host(); if your code accesses the Host header directly from request.META you are bypassing this security protection.
#More info: https://docs.djangoproject.com/en/1.7/ref/settings/#allowed-hosts

# set a value for production environment, alongside with debug set to false
ALLOWED_HOSTS = get_from_env('ALLOWED_HOSTS', 'localhost').split(",")

# Make this unique, and don't share it with anybody.
SECRET_KEY = get_from_env('SECRET_KEY', 'replaceme')
ROOT_URLCONF = 'urls'

ROOT_PATH = os.path.dirname(__file__)

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
        'NAME': 'helios'
    }
}

SOUTH_DATABASE_ADAPTERS = {'default':'south.db.postgresql_psycopg2'}

# override if we have an env variable
if get_from_env('DATABASE_URL', None):
    import dj_database_url
    DATABASES['default'] =  dj_database_url.config()
    DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql_psycopg2'
    DATABASES['default']['CONN_MAX_AGE'] = 600

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Sao_Paulo'
LANGUAGE_CODE = 'pt-br'
SITE_ID = 1
USE_I18N = True
USE_TZ = True

LANGUAGES = (
    ('en', _('English')),
    ('pt-br', _('Brazilian Portuguese')),
)

LOCALE_PATHS = (
    ROOT_PATH + '/locale',
)


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

STATIC_ROOT = ROOT_PATH + '/sitestatic'

STATICFILES_DIRS = (
    ROOT_PATH + '/helios/media',
    ROOT_PATH + '/heliosbooth',
    ROOT_PATH + '/heliosverifier',
    ROOT_PATH + '/helios_auth/media',
    ROOT_PATH + '/server_ui/media',
    ROOT_PATH + '/heliosinstitution/media/',
)


# Secure Stuff
if (get_from_env('SSL', '0') == '1'):
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True

    # tuned for Heroku
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_HTTPONLY = True

# let's go with one year because that's the way to do it now
STS = False
if (get_from_env('HSTS', '0') == '1'):
    STS = True
    # we're using our own custom middleware now
    # SECURE_HSTS_SECONDS = 31536000
    # not doing subdomains for now cause that is not likely to be necessary and can screw things up.
    # SECURE_HSTS_INCLUDE_SUBDOMAINS = True

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader'
)

MIDDLEWARE_CLASSES = (
    # make all things SSL
    #'sslify.middleware.SSLifyMiddleware',

    # secure a bunch of things
    'djangosecure.middleware.SecurityMiddleware',
    'helios.security.HSTSMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware'

   # 'flatpages_i18n.middleware.FlatpageFallbackMiddleware'
)


TEMPLATE_DIRS = (
    ROOT_PATH,
    os.path.join(ROOT_PATH, 'templates')
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'djangosecure',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django.contrib.messages',
    'django.contrib.admin',
    ## needed for queues
    'djcelery',
    'kombu.transport.django',
    ## in Django 1.7 we now use built-in migrations, no more south
    ## 'south',
    ## HELIOS stuff
    'helios_auth.apps.HeliosAuthConfig',
    'helios.apps.HeliosConfig',
    'server_ui',
    'helioslog.apps.HeliosLogConfig',
    'heliosinstitution.apps.HeliosInstitutionConfig',
)

##
## HELIOS
##


MEDIA_ROOT = ROOT_PATH + "media/"

# a relative path where voter upload files are stored
VOTER_UPLOAD_REL_PATH = "voters/%Y/%m/%d"


# Change your email settings
DEFAULT_FROM_EMAIL = get_from_env('DEFAULT_FROM_EMAIL', 'heliosvoting.pt@gmail.com')
DEFAULT_FROM_NAME = get_from_env('DEFAULT_FROM_NAME', 'Sistema de Votação Eletrônica')
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
SITE_TITLE = get_from_env('SITE_TITLE', _('Helios E-Voting System'))
MAIN_LOGO_URL = get_from_env('MAIN_LOGO_URL', '/static/logo.png')
ALLOW_ELECTION_INFO_URL = (get_from_env('ALLOW_ELECTION_INFO_URL', '0') == '1')

# FOOTER links
FOOTER_LINKS = json.loads(get_from_env('FOOTER_LINKS', '[]'))
FOOTER_LOGO_URL = get_from_env('FOOTER_LOGO_URL', None)

WELCOME_MESSAGE = get_from_env('WELCOME_MESSAGE', _('Welcome to Helios E-Voting System'))

HELP_EMAIL_ADDRESS = get_from_env('HELP_EMAIL_ADDRESS', 'shirlei@gmail.com')

AUTH_TEMPLATE_BASE = "server_ui/templates/base.html"
HELIOS_TEMPLATE_BASE = "server_ui/templates/base.html"
HELIOS_ADMIN_ONLY = False
HELIOS_VOTERS_UPLOAD = True
HELIOS_VOTERS_EMAIL = True

# are elections private by default?
HELIOS_PRIVATE_DEFAULT = False

# authentication systems enabled
#AUTH_ENABLED_AUTH_SYSTEMS = ['password','facebook','twitter', 'google', 'yahoo']
AUTH_ENABLED_AUTH_SYSTEMS = get_from_env('AUTH_ENABLED_AUTH_SYSTEMS', 'shibboleth').split(",")
AUTH_DEFAULT_AUTH_SYSTEM = get_from_env('AUTH_DEFAULT_AUTH_SYSTEM', None)

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
    level = logging.DEBUG,
    format = '%(asctime)s %(levelname)s %(message)s'
)


# set up django-celery
# BROKER_BACKEND = "kombu.transport.DatabaseTransport"
BROKER_URL = "django://"
CELERY_RESULT_DBURI = DATABASES['default']
import djcelery
djcelery.setup_loader()

CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'

CELERY_TASK_RESULT_EXPIRES = 5184000 # 60 days
# for testing
TEST_RUNNER = 'djcelery.contrib.test_runner.CeleryTestSuiteRunner'
# this effectively does CELERY_ALWAYS_EAGER = True

# see configuration example at https://pythonhosted.org/django-auth-ldap/example.html
AUTH_LDAP_SERVER_URI = "ldap://ldap.forumsys.com" # replace by your Ldap URI
AUTH_LDAP_BIND_DN = "cn=read-only-admin,dc=example,dc=com"
AUTH_LDAP_BIND_PASSWORD = "password"
AUTH_LDAP_USER_SEARCH = LDAPSearch("dc=example,dc=com",
    ldap.SCOPE_SUBTREE, "(cn=%(user)s)"
)

AUTH_LDAP_USER_ATTR_MAP = {
    "first_name": "givenName",
    "last_name": "sn",
    "email": "mail",
}

AUTH_LDAP_GROUP_TYPE = GroupOfNamesType(name_attr="cn")

AUTH_LDAP_FIND_GROUP_PERMS = True

AUTH_LDAP_BIND_AS_AUTHENTICATING_USER = True
AUTH_LDAP_CACHE_GROUPS = True
AUTH_LDAP_GROUP_CACHE_TIMEOUT = 3600

AUTH_LDAP_ALWAYS_UPDATE_USER = False

# Shibboleth auth settings
SHIBBOLETH_ATTRIBUTE_MAP = { 
    #"Shibboleth-givenName": (True, "first_name"),
    "Shib-inetOrgPerson-cn": (True, "common_name"),
    "Shib-inetOrgPerson-sn": (True, "last_name"),
    "Shib-inetOrgPerson-mail": (True, "email"),
    "Shib-eduPerson-eduPersonPrincipalName": (True, "eppn"),
    "Shib-brEduPerson-brEduAffiliationType": (True, "affiliation"),
    "Shib-Identity-Provider": (True, "identity_provider"),
}

FEDERATION_NAME = "CAFe Expresso"

# To use some manager-specific attributes, like idp address
USE_ELECTION_MANAGER_ATTRIBUTES = True

ELECTION_MANAGER_ATTRIBUTES = ['Provider']

INSTITUTION_ROLE = ['Institution Admin','Election Admin']

ATTRIBUTES_AUTOMATICALLY_CHECKED = ['brExitDate']

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

USE_EMBEDDED_DS = False
# end shibboleth auth settings
# Rollbar Error Logging
ROLLBAR_ACCESS_TOKEN = get_from_env('ROLLBAR_ACCESS_TOKEN', None)
if ROLLBAR_ACCESS_TOKEN:
  print "setting up rollbar"
  MIDDLEWARE_CLASSES += ('rollbar.contrib.django.middleware.RollbarNotifierMiddleware',)
  ROLLBAR = {
    'access_token': ROLLBAR_ACCESS_TOKEN,
    'environment': 'development' if DEBUG else 'production',  
  }
