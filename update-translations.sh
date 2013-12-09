#!/bin/bash

for d in zeus helios heliosauth server_ui; do
cd $d;
DJANGO_SETTINGS_MODULE=settings;
PYTHONPATH=..;
django-admin makemessages -l el -e .html -e .txt;
django-admin compilemessages;
cd ..;
done;
