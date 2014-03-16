#!/bin/bash

for d in zeus helios heliosauth server_ui; do
cd $d;
DJANGO_SETTINGS_MODULE=settings;
PYTHONPATH=..;
django-admin compilemessages;
cd ..;
done;
cd zeus/static/booth;
django-admin compilemessages;
