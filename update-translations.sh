#!/bin/bash

export PYTHONPATH=`pwd`
export DJANGO_SETTINGS_MODULE=settings;
export DJANGO_ADMIN=`which django-admin`;
if [ -f `which django-admin.py` ]; then
    DJANGO_ADMIN=`which django-admin.py`;
fi

for d in zeus helios heliosauth server_ui account_administration; do
  cd $d;
  $DJANGO_ADMIN makemessages --no-location -l el -e .html -e .txt;
  cd ..;
done;

python manage.py makeboothmessages --no-location -l en -l el -e .html -e .js;
