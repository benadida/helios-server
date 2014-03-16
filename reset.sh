#!/bin/bash
dropdb helios
createdb helios
python manage.py syncdb
python manage.py migrate
echo "from helios_auth.models import User; User.objects.create(user_type='google', user_id='p.maene@gmail.com', name='Pieter Maene', info={'email':'p.maene@gmail.com'})" | python manage.py shell
