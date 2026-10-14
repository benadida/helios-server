"""Strict ALU backend settings for Cloudflare Containers."""
import os
import re
import uuid
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured
from settings import *
from helios_auth.bridge_protocol import https_origin

for key in ('DATABASE_URL', 'SECRET_KEY', 'EMAIL_OPTOUT_SECRET',
            'ALU_BRIDGE_SECRET', 'ALU_BRIDGE_APP_ORIGIN', 'URL_HOST', 'RECOVERY_SECRET'):
    if not os.environ.get(key):
        raise ImproperlyConfigured(f'Missing Cloudflare backend setting: {key}')
for key in ('SECRET_KEY', 'EMAIL_OPTOUT_SECRET', 'ALU_BRIDGE_SECRET', 'RECOVERY_SECRET'):
    if len(os.environ[key].encode()) < 32:
        raise ImproperlyConfigured(f'{key} must contain at least 32 bytes.')

URL_HOST = SECURE_URL_HOST = https_origin(os.environ['URL_HOST'])
ALLOWED_HOSTS = [urlsplit(URL_HOST).hostname, 'containerstarthealthcheck', 'ping']
MIDDLEWARE = ['helios.runtime_health.ContainerHealthMiddleware', *MIDDLEWARE]
ALU_BRIDGE_APP_ORIGIN = https_origin(ALU_BRIDGE_APP_ORIGIN)
if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', ALU_BRIDGE_CLIENT_ID):
    raise ImproperlyConfigured('Invalid bridge client identifier.')
if any(str(uuid.UUID(value)) != value for value in ALU_BRIDGE_ELECTIONS):
    raise ImproperlyConfigured('Use canonical comma-separated election UUIDs.')

DEBUG = False
AUTH_ENABLED_SYSTEMS = ['alu']
AUTH_DEFAULT_SYSTEM = 'alu'
ALU_STUDENT_DOMAIN = 'alustudent.com'
HELIOS_ADMIN_ONLY = True
HELIOS_VOTERS_UPLOAD = False
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = True
TIME_ZONE = 'Africa/Kigali'
ALU_VOTE_VERIFICATION_BACKEND = 'database'
RECOVERY_SECRET = os.environ['RECOVERY_SECRET']
# Vote verification uses the durable database queue. Legacy tally/notification
# tasks still run synchronously; frontend transactional emails are unaffected.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = 'memory://'
EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'
