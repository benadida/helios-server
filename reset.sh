#!/bin/bash
dropdb helios
createdb helios
python manage.py syncdb
python manage.py migrate
#echo "from helios_auth.models import User; User.objects.create(user_type='google',user_id='shirlei@gmail.com', info={'name':'Shirlei Chaves'})" | python manage.py shell
