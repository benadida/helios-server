"""
# to run tests
$ export PYTHONPATH=.
$ python manage.py test helios --settings=test_settings
"""

from settings import *

import os, errno
import datetime

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

ZEUS_ELECTION_STREAM_HANDLER = True


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

TESTS_DIR = os.environ.get('ZEUS_TESTS_DIR', '/tmp/zeus-tests')
PROJECT_ROOT = '%s/%s' % (TESTS_DIR, datetime.datetime.now())
ZEUS_ELECTION_LOG_DIR = os.path.join(PROJECT_ROOT, 'election_logs')
ZEUS_PROOFS_PATH = os.path.join(PROJECT_ROOT, 'proofs')
ZEUS_RESULTS_PATH = os.path.join(PROJECT_ROOT, 'results')
ZEUS_MIXES_PATH = os.path.join(PROJECT_ROOT, 'mixes')

dirs = [ZEUS_ELECTION_LOG_DIR, ZEUS_PROOFS_PATH,
        ZEUS_RESULTS_PATH, ZEUS_MIXES_PATH]
for dir in dirs:
    mkdir_p(dir)
