#!/bin/bash
dropdb helios
createdb helios
python manage.py syncdb
python manage.py migrate
echo "from auth.models import User; User.objects.create(user_type='password',user_id='robbert', info={'name':'robbert','password':'password'})" | python manage.py shell


