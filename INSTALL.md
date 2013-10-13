* install PostgreSQL 8.3+

* make sure you have virtualenv installed:
http://www.virtualenv.org/en/latest/

* download helios-server

* cd into the helios-server directory

* create a virtualenv:

```
virtualenv venv
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
