web: gunicorn wsgi:application
worker: python manage.py celeryd -E -B --beat