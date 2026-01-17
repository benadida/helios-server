# Helios Server Installation

## Prerequisites

* Install PostgreSQL 12+

* Install RabbitMQ
  This is needed for Celery to work, which does background processing such as
  the processing of uploaded list-of-voter CSV files.

* Download helios-server

* `cd` into the helios-server directory

## Python Setup

* Install Python 3.13 including dev packages

```
sudo apt install python3 python3-dev
```

* Install uv (modern Python package manager)

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

* You'll also need Postgres dev libraries. For example on Ubuntu:

```
sudo apt install libpq-dev
```

* Install dependencies (uv creates a virtual environment automatically)

```
uv sync
```

## Database Setup

* Reset database

```
./reset.sh
```

## Running the Server

* Start server

```
uv run python manage.py runserver
```

## Google Auth Configuration

To get Google Auth working:

* Go to https://console.developers.google.com

* Create an application

* Set up OAuth2 credentials as a web application, with your origin, e.g. `https://myhelios.example.com`, and your auth callback, which based on our example is `https://myhelios.example.com/auth/after/`

* In the developer console, enable the Google People API

* Set the `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` configuration variables accordingly
