#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status.
dropdb helios
createdb helios
python manage.py syncdb
python manage.py migrate
#echo "from helios_auth.models import User; User.objects.create(user_type='google',user_id='shirlei@gmail.com', info={'name':'Shirlei Chaves'})" | python manage.py shell
