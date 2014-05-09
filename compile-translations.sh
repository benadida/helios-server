#!/bin/bash

export DJANGO_SETTINGS_MODULE=settings
export PYTHONPATH=`pwd`
export DJANGO_ADMIN=`which django-admin`;
if [ -f `which django-admin.py` ]; then
    DJANGO_ADMIN=`which django-admin.py`;
fi

for d in zeus helios heliosauth server_ui account_administration; do
  cd $d;
  $DJANGO_ADMIN compilemessages;
  cd ..;
done;

cd zeus/static/booth;
$DJANGO_ADMIN compilemessages;
