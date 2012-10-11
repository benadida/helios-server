#!/bin/bash
dropdb helios
createdb helios
python manage.py syncdb
python manage.py migrate zeus
python manage.py migrate heliosauth
python manage.py migrate
echo "from zeus.models import Faculty; Faculty.objects.create(name='University 1 name')" | python manage.py shell
echo "from heliosauth.models import User;
User.objects.create(user_type='password',faculty_id=1,admin_p=True,user_id='kpap@grnet.gr',info={'name':'Kostas Papadimitriou', 'password': '123'})" | python manage.py shell
