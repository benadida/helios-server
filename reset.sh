#!/bin/bash
dropdb zeus
createdb zeus
python manage.py syncdb --all
python manage.py migrate --fake
python manage.py manage_users --create-institution GRNET
python manage.py manage_users kpap --create-user --institution=1
