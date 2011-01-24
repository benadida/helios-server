#!/bin/bash
dropdb helios
createdb helios
python manage.py syncdb
python manage.py migrate
echo "from auth.models import User; User.update_or_create(user_type='google',user_id='ben@adida.net',info={})" | python manage.py shell