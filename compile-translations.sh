#!/bin/bash

export DJANGO_SETTINGS_MODULE=settings
export PYTHONPATH=`pwd`

for d in zeus helios heliosauth server_ui account_administration; do
  cd $d;
  django-admin compilemessages;
  cd ..;
done;

cd zeus/static/booth;
django-admin compilemessages;
