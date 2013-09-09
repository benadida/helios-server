#!/bin/bash

for d in zeus helios heliosauth server_ui; do
cd $d;
django-admin makemessages -l el;
django-admin compilemessages;
cd ..;
done;
