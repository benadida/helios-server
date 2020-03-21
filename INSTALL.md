* install PostgreSQL 8.3+

* make sure you have pipenv installed: https://pypi.org/project/pipenv/

* download helios-server

* cd into the helios-server directory

* install all the things:

```
pipenv install
```

* activate virtual environment

```
pipenv shell
````

* reset database

```
./reset.sh
```

* start server

```
python manage.py runserver
```

* to get Google Auth working:

** go to https://console.developers.google.com

** create an application

** set up oauth2 credentials as a web application, with your origin, e.g. https://myhelios.example.com, and your auth callback, which, based on our example, is https://myhelios.example.com/auth/after/

** still in the developer console, enable the Google+ API.

** set the GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET configuration variables accordingly.
