# Helios Server Installation

## Prerequisites

* Install PostgreSQL 12+

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

* Start the background task worker, which verifies cast votes, sends emails,
  processes voter files and computes tallies.

```
uv run python manage.py db_worker
```

## Background Tasks

Background tasks are queued in the PostgreSQL database (with `django-tasks` and its
`django-tasks-db` backend); there is no separate message broker. Every task goes
through this queue, so without a running `db_worker`, cast votes stay unverified,
emails aren't sent and tallies aren't computed, in development too.

* The worker runs one task at a time. To run more at once, start more `db_worker`
  processes; each task is claimed by only one of them.

* Cast vote verification runs ahead of other waiting tasks such as bulk voter emails.

* Finished tasks stay in the database; prune them regularly, e.g. daily:

```
uv run python manage.py prune_db_task_results
```

* A worker killed mid-task leaves that task stuck as running. Put tasks running longer than 120 minutes back in the queue (bulk voter emails are listed, not requeued):

```
uv run python manage.py requeue_stuck_tasks --older-than 120
```

* The stats page shows how many tasks are waiting, running, stuck and failed in
  the last day, and how many votes are waiting for verification; "force it"
  re-queues them.

## Upgrading from Celery and RabbitMQ

Older versions of Helios used Celery with RabbitMQ. To upgrade:

* Deploy at a quiet time, since tasks still waiting in RabbitMQ won't be run.

* Run `uv run python manage.py migrate` to create the task table, and replace the
  Celery worker with `db_worker` (see `Procfile`).

* On the stats page, use "force it" to re-queue any cast votes that were still unverified.

* Remove RabbitMQ and the `CELERY_BROKER_URL` setting.

## Deploying

* **Heroku** uses the `Procfile`.

* **Fly.io** uses `fly.toml` and the `Dockerfile`; the steps for a first deploy are at
  the top of `fly.toml`. To move an existing Heroku deployment, see
  [docs/migrating-heroku-to-fly.md](docs/migrating-heroku-to-fly.md).

* Either way, set `DEBUG=0` in production: it defaults to on, which enables the
  `devlogin` auth system.

## Google Auth Configuration

To get Google Auth working:

* Go to https://console.developers.google.com

* Create an application

* Set up OAuth2 credentials as a web application, with your origin, e.g. `https://myhelios.example.com`, and your auth callback, which based on our example is `https://myhelios.example.com/auth/after/`

* In the developer console, enable the Google People API

* Set the `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` configuration variables accordingly
