# Helios Server Installation

## Prerequisites

* Install PostgreSQL 12+

* Install RabbitMQ
  This is needed for Celery to work, which does background processing such as
  the processing of uploaded list-of-voter CSV files.

* Download helios-server

* `cd` into the helios-server directory

## Python Setup

* Install Python 3.12 including dev and venv packages

```
sudo apt install python3 python3-dev python3-venv python3-pip
```

* Create a virtualenv

```
python3 -m venv venv
```

* You'll also need Postgres dev libraries. For example on Ubuntu:

```
sudo apt install libpq-dev
```

* Activate virtual environment

```
source venv/bin/activate
```

* Install requirements

```
pip install -r requirements.txt
```

## Database Setup

* Reset database

```
./reset.sh
```

## Running the Server

* Start server

```
python manage.py runserver
```

## Google Auth Configuration

To get Google Auth working:

* Go to https://console.developers.google.com

* Create an application

* Set up OAuth2 credentials as a web application, with your origin, e.g. `https://myhelios.example.com`, and your auth callback, which based on our example is `https://myhelios.example.com/auth/after/`

* In the developer console, enable the Google People API

* Set the `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` configuration variables accordingly
