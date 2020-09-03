#!/bin/bash
virtualenv /venv
source /venv/bin/activate
pip install --quiet --no-cache-dir -r requirements.txt
python manage.py compilemessages
python manage.py collectstatic --no-input
python manage.py migrate
echo "from django.contrib.auth.models import User; 
from django.contrib.auth.hashers import make_password; 
User.objects.create(is_staff='true',is_superuser='true', username='$DJANGO_SUPERUSER_USERNAME', email='$DJANGO_SUPERUSER_EMAIL', password=make_password('$DJANGO_SUPERUSER_PASSWORD'))" | python manage.py shell

service supervisor start

exec "$@"