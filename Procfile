web: gunicorn wsgi:application -b 0.0.0.0:$PORT -w 8
worker: python manage.py celeryd -E -B --beat --concurrency=1