"""
# to run tests
$ export PYTHONPATH=.
$ python manage.py test helios --settings=test_settings
"""

from settings import *

DEBUG = False

#DATABASES = {
    #'default': {
        #'ENGINE': 'django.db.backends.postgresql_psycopg2',
        #'NAME': 'helios',
        #'HOST': '/tmp/',
        #'PORT': 5433 # in memory post
    #}
#}

CELERY_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

SOUTH_TESTS_MIGRATE = False
#DATABASES = {
    #'default': {
        #'ENGINE': 'django.db.backends.sqlite3',
        #'NAME': ':memory:'
    #}
#}

import multiprocessing
ZEUS_MIXNET_NR_PARALLEL = multiprocessing.cpu_count()
ZEUS_MIXNET_NR_ROUNDS = 16
