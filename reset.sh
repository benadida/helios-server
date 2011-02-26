#!/bin/bash
dropdb helios
createdb helios
python manage.py syncdb
python manage.py migrate
echo "from auth.models import User; User.objects.create(user_type='google',user_id='ben@adida.net', info={'name':'Ben Adida'})" | python manage.py shell