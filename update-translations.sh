#!/bin/bash

for d in zeus helios heliosauth server_ui; do
cd $d;
DJANGO_SETTINGS_MODULE=settings;
PYTHONPATH=..;
django-admin.py makemessages -l el;
django-admin.py compilemessages;
cd ..;
done;
