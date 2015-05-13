#!/bin/bash

export PYTHONPATH=`pwd`;
export DJANGO_SETTINGS_MODULE=settings;
export DJANGO_ADMIN=`which django-admin`;
export VENV_DJANGO_ADMIN=`which django-admin.py`;

if [ -n "$VENV_DJANGO_ADMIN" ] 
then
    DJANGO_ADMIN=$VENV_DJANGO_ADMIN;
fi

for d in zeus helios heliosauth server_ui account_administration; do
  echo $d
  cd $d;
  $DJANGO_ADMIN makemessages --no-location -l el -e .html -e .txt || true;
  cd ..;
done;

python manage.py makeboothmessages --no-location -l en -l el -e .html -e .js;
