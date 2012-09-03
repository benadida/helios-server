"""
# to run tests
$ export PYTHONPATH=.
$ python manage.py test helios --settings=test_settings
"""

from settings import *

DEBUG = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'
    }
}
