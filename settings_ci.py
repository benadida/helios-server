# CI-specific settings that override database configuration for GitHub Actions
from settings import *

# Override database settings for CI environment
# This is needed because the main settings.py ignores environment variables during testing
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'helios',
        'HOST': 'localhost',
        'PORT': '5432',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'CONN_MAX_AGE': 600,
    },
}
