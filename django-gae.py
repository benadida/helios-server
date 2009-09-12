"""
Running Django on GAE, as per
http://code.google.com/appengine/articles/django.html

Ben Adida
ben@adida.net
2009-07-11
"""

import logging, os

# Django 1.0
from google.appengine.dist import use_library
use_library('django', '1.0')

# Appengine Django Helper
from appengine_django import InstallAppengineHelperForDjango
InstallAppengineHelperForDjango()

# Google App Engine imports.
from google.appengine.ext.webapp import util

# Force Django to reload its settings.
from django.conf import settings
settings._target = None

# Must set this env var before importing any part of Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import logging
import django.core.handlers.wsgi
import django.core.signals
import django.db
import django.dispatch.dispatcher

def main():
  # Create a Django application for WSGI.
  application = django.core.handlers.wsgi.WSGIHandler()
  
  # if there's initialiation, run it
  import initialization

  # Run the WSGI CGI handler with that application.
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()