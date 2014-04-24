#!/bin/bash

export PYTHONPATH=`pwd`
export DJANGO_SETTINGS_MODULE=settings;
for d in zeus helios heliosauth server_ui account_administration; do
  cd $d;
  django-admin makemessages --no-location -l el -e .html -e .txt;
  #django-admin makemessages -l en -e .html -e .txt;
  cd ..;
done;

python manage.py makeboothmessages --no-location -l en -l el -e .html -e .js;
