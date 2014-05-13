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
  cd $d;
  $DJANGO_ADMIN compilemessages;
  cd ..;
done;

cd zeus/static/booth;
$DJANGO_ADMIN compilemessages;
