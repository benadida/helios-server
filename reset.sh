#!/bin/bash
dropdb helios
createdb helios
python manage.py syncdb
python manage.py migrate
echo "from auth.models import User; User.update_or_create(user_type='password',user_id='benadida',info={'password':'test'})" | python manage.py shell