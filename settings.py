
import os, json

##############################
# SETUP                      #
##############################

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# a massive hack to see if we're testing, in which case we use different settings
import sys
TESTING = 'test' in sys.argv

# go through environment variables and override them
def get_from_env(var, default):
    #if not TESTING and os.environ.has_key(var):
    if not TESTING and var in os.environ:
        return os.environ[var]
    else:
        return default

DEBUG = (get_from_env('DEBUG', '1') == '1')
TEMPLATE_DEBUG = DEBUG

# add admins of the form:  ('Ben Adida', 'ben@adida.net'),
# if you want to be emailed about errors.
# Django docs: A list of all the people who get code error notifications.
ADMINS = (
    ('Warwick McNaughton', 'warwick.mcnaughton@gmail.com'),
)

# Django docs: A list in the same format as ADMINS that specifies 
# who should get broken link notifications when 
# BrokenLinkEmailsMiddleware is enabled.
MANAGERS = ADMINS

# set up logging
import logging
logging.basicConfig(
    level = logging.DEBUG,
    format = '%(asctime)s %(levelname)s %(message)s'
)

##############################
# HOSTS                      #
##############################

# The two hosts are here so the main site can be over plain HTTP
# while the voting URLs are served over SSL.
# IMPORTANT: you should not change the SECURE_URL_HOST setting once you've created
# elections, as your elections' cast_url will then be incorrect 
# (it is stored in database and does not change).
# Don't use:  SECURE_URL_HOST = "https://localhost:8443"

PRODUCTION = False

if PRODUCTION:
    URL_HOST = "https://voting-app-82048.appspot.com"
    SECURE_URL_HOST = "https://voting-app-82048.appspot.com"

else:
    URL_HOST = get_from_env("URL_HOST", "http://localhost:8000").rstrip("/")
    SECURE_URL_HOST = get_from_env("SECURE_URL_HOST", URL_HOST).rstrip("/")    


# If debug is set to false and ALLOWED_HOSTS is not declared, django raises  
# "CommandError: You must set settings.ALLOWED_HOSTS if DEBUG is False."
# If in production, you got a bad request (400) error
# More info: https://docs.djangoproject.com/en/1.7/ref/settings/#allowed-hosts (same for 1.6)

# ALLOWED_HOSTS = get_from_env('ALLOWED_HOSTS', 'localhost').split(",")

# SECURITY WARNING: App Engine's security features ensure that it is safe to
# have ALLOWED_HOSTS = ['*'] when the app is deployed. If you deploy a Django
# app not on App Engine, make sure to set an appropriate host here.
# See https://docs.djangoproject.com/en/2.1/ref/settings/
ALLOWED_HOSTS = ['*']


##############################
# DATABASES                  #
##############################

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'helios',
        'USER': 'warwickmcnaughton',
        'PASSWORD': '1629',
    }
}



##############################
# URLS / DIRECTORIES         #
##############################

# Absolute filesystem path to the directory that will hold user-uploaded files.
# https://docs.djangoproject.com/en/2.1/ref/settings/#media-root
# MEDIA_ROOT and STATIC_ROOT must have different values. Before STATIC_ROOT was introduced, 
# it was common to rely or fallback on MEDIA_ROOT to also serve static files; 
# however, since this can have serious security implications, there is a validation check to prevent it.
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT, used for managing stored files. 
# It must end in a slash if set to a non-empty value. You will need to configure these files to be 
# served in both development and production environments.
MEDIA_URL = ''


# This should be an initially empty destination directory for collecting your static files from their permanent 
# locations into one directory for ease of deployment; it is not a place to store your static files permanently. 
# You should do that in directories that will be found by staticfiles’s finders, which by default, 
# are 'static/' app sub-directories and any directories you include in STATICFILES_DIRS).
# https://docs.djangoproject.com/en/2.1/ref/settings/#std:setting-STATIC_ROOT
STATIC_ROOT = 'static/'

# URL to use when referring to static files located in STATIC_ROOT.
STATIC_URL = '/static/'

# This setting defines the additional locations the staticfiles app will traverse 
# if the FileSystemFinder finder is enabled, e.g. if you use the collectstatic or findstatic management command 
# or use the static file serving view.
STATICFILES_DIRS = [
    "server_ui/static/",
    "helios_auth/static/",
    "helios/static/",
]

ROOT_URLCONF = 'urls'

ROOT_PATH = os.path.dirname(__file__)



##############################
# SECURITY                   #
##############################

# Make this unique, and don't share it with anybody.
SECRET_KEY = get_from_env('SECRET_KEY', 'replaceme')

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


##############################
# APPS / TEMPLATES           #
##############################

MIDDLEWARE = (
    # make all things SSL
    #'sslify.middleware.SSLifyMiddleware',

    # secure a bunch of things
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'helios.security.hsts_middleware'
)

ROOT_PATH = os.path.dirname(__file__)


INSTALLED_APPS = (
   'django.contrib.auth',
   'django.contrib.contenttypes',
    # 'djangosecure',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    #'django.contrib.sites',
    ## needed for queues
    #'djcelery',
    #'kombu.transport.django',
    ## HELIOS stuff
    'helios_auth',
    'helios',
    'server_ui',
)


ROOT_URLCONF = 'urls'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [ROOT_PATH],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


##############################
# TIME, LANGUAGE             #
##############################

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
# TIME_ZONE = 'America/Los_Angeles'
TIME_ZONE = 'Pacific/Auckland'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'


# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True


##############################
# HELIOS                     #
##############################



# is this the master Helios web site?
MASTER_HELIOS = (get_from_env('MASTER_HELIOS', '0') == '1')

# show ability to log in? (for example, if the site is mostly used by voters)
# if turned off, the admin will need to know to go to /auth/login manually
SHOW_LOGIN_OPTIONS = (get_from_env('SHOW_LOGIN_OPTIONS', '1') == '1')

# sometimes, when the site is not that social, it's not helpful
# to display who created the election
SHOW_USER_INFO = (get_from_env('SHOW_USER_INFO', '1') == '1')

# Absolute filesystem path to the directory that will hold user-uploaded files.
# https://docs.djangoproject.com/en/2.1/ref/settings/#media-root
MEDIA_ROOT = BASE_DIR + "media/"

# a relative path where voter upload files are stored
VOTER_UPLOAD_REL_PATH = "voters/%Y/%m/%d"

SITE_ID = 1

# Change your email settings
DEFAULT_FROM_EMAIL = get_from_env('DEFAULT_FROM_EMAIL', 'warwick.mcnaughton@gmail.com')
DEFAULT_FROM_NAME = get_from_env('DEFAULT_FROM_NAME', 'Warwick')
SERVER_EMAIL = '%s <%s>' % (DEFAULT_FROM_NAME, DEFAULT_FROM_EMAIL)

LOGIN_URL = '/auth/'
LOGOUT_ON_CONFIRMATION = True

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
#AUTH_ENABLED_AUTH_SYSTEMS = ['password','facebook','twitter', 'google', 'yahoo']
AUTH_ENABLED_AUTH_SYSTEMS = get_from_env('AUTH_ENABLED_AUTH_SYSTEMS', 'google').split(",")
AUTH_DEFAULT_AUTH_SYSTEM = get_from_env('AUTH_DEFAULT_AUTH_SYSTEM', None)

# google
GOOGLE_CLIENT_ID = get_from_env('GOOGLE_CLIENT_ID', '739721212934-9anb7pq77h6nglknafiiq6svb50a73mr.apps.googleusercontent.com')
GOOGLE_CLIENT_SECRET = get_from_env('GOOGLE_CLIENT_SECRET', ***REMOVED***)

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



##############################
# EMAIL                      #
##############################

# EMAIL_HOST = get_from_env('EMAIL_HOST', 'localhost')
# EMAIL_PORT = int(get_from_env('EMAIL_PORT', "2525"))
# EMAIL_HOST_USER = get_from_env('EMAIL_HOST_USER', '')
# EMAIL_HOST_PASSWORD = get_from_env('EMAIL_HOST_PASSWORD', '')
# EMAIL_USE_TLS = (get_from_env('EMAIL_USE_TLS', '0') == '1')
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
# EMAIL_FILE_PATH = '/Users/warwickmcnaughton/Projects/Helios/Voter_list' 


# to use AWS Simple Email Service
# in which case environment should contain
# # AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
# if get_from_env('EMAIL_USE_AWS', '0') == '1':
#     EMAIL_BACKEND = 'django_ses.SESBackend'




##############################
# CELERY                     #
##############################

CELERY_BROKER_URL = 'amqp://localhost'
CELERY_RESULT_BACKEND = 'rpc://'
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
# # App instance to use (value for --app argument).
# CELERY_APP="helios"
# # Absolute or relative path to the celery program.
# CELERY_BIN="venv/bin/celery"
# # List of node names to start (separated by space).
# CELERYD_NODES="worker1"
# Additional command-line arguments for the worker, see celery worker –help for a list. 
# CELERYD_OPTS=""
# Path to change directory to at start. Default is to stay in the current directory.
# CELERYD_CHDIR
# Full path to the PID file. Default is /var/run/celery/%n.pid
# CELERYD_PID_FILE
# Full path to the worker log file. Default is /var/log/celery/%n%I.log 
# Note: Using %I is important when using the prefork pool as having multiple processes share the same log file will lead to race conditions.
# CELERYD_LOG_FILE
# Worker log level. Default is INFO.
# CELERYD_LOG_LEVEL
# User to run the worker as. Default is current user.
# CELERYD_USER
# Group to run worker as. Default is current user.
# CELERYD_GROUP
# Always create directories (log directory and pid file directory). 
# Default is to only create directories when no custom logfile/pidfile set.
# CELERY_CREATE_DIRS
# Always create pidfile directory. By default only enabled when no custom pidfile location set.
# CELERY_CREATE_RUNDIR
# Always create logfile directory. By default only enable when no custom logfile location set.
# CELERY_CREATE_LOGDIR


##############################
# ROLLBAR                    #
##############################


# Rollbar Error Logging
ROLLBAR_ACCESS_TOKEN = get_from_env('ROLLBAR_ACCESS_TOKEN', None)
if ROLLBAR_ACCESS_TOKEN:
  print("setting up rollbar")
  MIDDLEWARE_CLASSES += ('rollbar.contrib.django.middleware.RollbarNotifierMiddleware',)
  ROLLBAR = {
    'access_token': ROLLBAR_ACCESS_TOKEN,
    'environment': 'development' if DEBUG else 'production',  
  }
