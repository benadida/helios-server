* install PostgreSQL 9.5+

* install Rabbit MQ
  This is needed for celery to work, which does background processing such as
  the processing of uploaded list-of-voter CSV files.  

* make sure you have virtualenv installed:
http://www.virtualenv.org/en/latest/

* download helios-server

* cd into the helios-server directory

* install Python3.6 including dev, pip, and venv

```
sudo apt install python3.6 python3.6-venv python3.6-pip python3.6-venv
```

* create a virtualenv

```
python3.6 -m venv $(pwd)/venv
```

* you'll also need Postgres dev libraries. For example on Ubuntu:

```
sudo apt install libpq-dev 
```

* activate virtual environment

```
source venv/bin/activate
````

* install requirements

```
pip install -r requirements.txt
```

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

** still in the developer console, enable the Google+ API and Google People API.

** set the GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET configuration variables accordingly.
