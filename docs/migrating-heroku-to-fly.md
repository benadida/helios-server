# Migrating a Helios deployment from Heroku to Fly.io

This guide moves an existing Helios server, with its database and live elections, from Heroku to Fly.io with a short maintenance window and a rollback path. New installs can skip to [Step 3](#step-3-create-the-fly-app).

Helios now keeps its background task queue in PostgreSQL (`django-tasks` with the `django-tasks-db` backend; see `INSTALL.md`, "Background Tasks"). There is no message broker, so **the database is the only stateful service to migrate**. It holds the elections, the voters, and every waiting background task. That makes the move simpler, but it means the database dump also carries the queue, which this guide handles explicitly.

It assumes the Fly support files from benadida/helios-server#482 (`Dockerfile`, `fly.toml`, `.dockerignore`), with these settings in `fly.toml`:

```toml
kill_signal = "SIGTERM"
kill_timeout = 300          # let db_worker finish the task it's running

[env]
  DEBUG = "0"
  SSL = "1"
  HSTS = "1"

[deploy]
  release_command = "/app/.venv/bin/python manage.py migrate --noinput"

[processes]
  web = "/app/.venv/bin/gunicorn wsgi:application -b 0.0.0.0:8080 -w 4"
  worker = "/app/.venv/bin/python manage.py db_worker"
```

If your `fly.toml` still has a `celery` worker command, replace it with `db_worker` as above. The notes in each step say what breaks if one of the other settings is missing.

> Fly's CLI and products change often. Check each `fly` command against `fly <command> --help` and the current Fly docs before running it.

---

## Before you start: four rules

1. **Don't migrate while an election is open for voting.** Pick a window with no election between "freeze" and "tally". Ballots cast on Heroku after the final database dump would be lost.
2. **Keep the same public URL.** Every election stores its `cast_url`, built from `SECURE_URL_HOST` at creation time. If voters reach Helios at `vote.example.org` today, they must reach it at `vote.example.org` on Fly too. You move the **domain**, not the URL. If you currently use `yourapp.herokuapp.com` directly, existing elections' links stay tied to Heroku. Either keep Heroku running until those elections are archived, or accept that their stored URLs will point at the old host.
3. **Copy secrets exactly, especially `SECRET_KEY` and `EMAIL_OPTOUT_SECRET`.** A new `SECRET_KEY` logs everyone out and invalidates in-flight signed tokens. A new `EMAIL_OPTOUT_SECRET` breaks every opt-out/opt-in link already sent to voters.
4. **Never run a worker against a restored copy you don't intend to go live with.** The dump includes waiting tasks, such as queued voter emails. A worker on a rehearsal copy would send them to real voters (see Step 5).

---

## Step 1: Inventory the Heroku app

```bash
heroku config -a YOUR_HEROKU_APP --shell > heroku.env
```
```bash
heroku addons -a YOUR_HEROKU_APP
```
```bash
heroku pg:info -a YOUR_HEROKU_APP
```

`heroku.env` contains secrets. Keep it out of the repo, and delete it when you're done.

Record:
- **Postgres version** (from `pg:info`). Create the Fly database on the same major version.
- **Which task queue Heroku runs.** If the Heroku `worker` dyno still runs `celery`, Heroku is on a pre-database-queue version. Upgrade Heroku first: follow "Upgrading from Celery and RabbitMQ" in `INSTALL.md`, then remove the RabbitMQ/CloudAMQP add-on. Do this before moving providers, so you aren't debugging two changes at once.
- **Heroku Scheduler jobs**, e.g. `prune_db_task_results` and `requeue_stuck_tasks`. They need a new home on Fly (Step 6).
- **Email provider** vars (`MAILGUN_API_KEY`, or `EMAIL_HOST`/`EMAIL_HOST_USER`/…, or `EMAIL_USE_AWS` + AWS keys).
- **Auth provider** vars (`GOOGLE_CLIENT_ID`, `GH_CLIENT_ID`, `AUTH_ENABLED_SYSTEMS`, …).
- `URL_HOST`, `SECURE_URL_HOST`, `ALLOWED_HOSTS`, `ROLLBAR_ACCESS_TOKEN`, and site branding vars.

## Step 2: Choose the database

| Option | `DATABASE_SSL_REQUIRE` | Notes |
|---|---|---|
| Fly Managed Postgres | `1` (default) | Fly operates backups and failover. Recommended for production. |
| `fly postgres create` (unmanaged) | `0` | You operate it. The URL from `fly postgres attach` uses the private network without TLS. |
| Keep an external DB (e.g. stay on Heroku Postgres, RDS) | `1` | No data move at all, but every query, and every worker poll, crosses providers. |

`settings.py` reads `DATABASE_SSL_REQUIRE` and defaults to `1`, which forces `sslmode=require`. Set it to `0` **only** for a database reached over Fly's private network without TLS. Otherwise connections fail with an SSL error.

The database now carries the task queue too. The worker polls it when idle, and cast-vote verification waits on it. So put the database in the same Fly region as the app (`primary_region`). Size its connection limit for:

- web machines × gunicorn workers (connections persist for 10 minutes, `CONN_MAX_AGE = 600`), plus
- one connection per `db_worker`, plus
- headroom for `fly ssh console` sessions.

## Step 3: Create the Fly app

```bash
fly auth login
```
```bash
fly launch --no-deploy --copy-config --name YOUR_FLY_APP
```

This keeps the repo's `fly.toml` but rewrites `app = …`. Check `primary_region`.

Then create and attach the database. For unmanaged Postgres:

```bash
fly postgres create --name YOUR_FLY_APP-db --region iad
```
```bash
fly postgres attach YOUR_FLY_APP-db --app YOUR_FLY_APP
```

`attach` sets the `DATABASE_URL` secret. For Managed Postgres or an external database, set `DATABASE_URL` yourself in Step 4.

## Step 4: Set secrets

Copy the values from `heroku.env`. These are required:

```bash
fly secrets set --stage -a YOUR_FLY_APP \
  SECRET_KEY='…same as Heroku…' \
  EMAIL_OPTOUT_SECRET='…same as Heroku…' \
  URL_HOST='https://vote.example.org' \
  SECURE_URL_HOST='https://vote.example.org' \
  ALLOWED_HOSTS='vote.example.org,YOUR_FLY_APP.fly.dev'
```

If you're on unmanaged Fly Postgres, set this one too:

```bash
fly secrets set --stage -a YOUR_FLY_APP DATABASE_SSL_REQUIRE=0
```

Auth and monitoring vars, as applicable:

```bash
fly secrets set --stage -a YOUR_FLY_APP \
  GOOGLE_CLIENT_ID='…' GOOGLE_CLIENT_SECRET='…' \
  ROLLBAR_ACCESS_TOKEN='…'
```

**Hold off on the email credentials** (`MAILGUN_API_KEY`, SMTP or SES vars) until cutover (Step 7). Without them, nothing the rehearsal does can email a real voter.

Notes:
- `DEBUG`, `SSL`, and `HSTS` should be in `fly.toml` `[env]`. If they aren't, set them as secrets. **Never deploy with `DEBUG` unset**: it defaults to on, which enables the `devlogin` auth system and lets anyone log in as any user.
- `ALLOWED_HOSTS` must include the `.fly.dev` hostname so you can test before DNS moves.
- Don't copy `CELERY_BROKER_URL`, `CLOUDAMQP_*`, `PORT`, `HEROKU_*`, or Heroku's `DATABASE_URL`.
- OAuth providers (Google, GitHub, GitLab, Facebook): redirect URIs are based on `URL_HOST`. Since the host isn't changing, nothing needs updating. To test logins on `*.fly.dev` before cutover, temporarily add that redirect URI in each provider's console.

`--stage` stores the secrets without restarting anything (there's nothing deployed yet).

## Step 5: Rehearsal: deploy with a copy of the data

Do a full dry run first, while Heroku keeps serving traffic.

1. Take and download a Heroku backup:
   ```bash
   heroku pg:backups:capture -a YOUR_HEROKU_APP
   ```
   ```bash
   curl -o helios.dump "$(heroku pg:backups:url -a YOUR_HEROKU_APP)"
   ```
2. Open a tunnel to the Fly database (in a separate terminal):
   ```bash
   fly proxy 15432:5432 -a YOUR_FLY_APP-db
   ```
3. Restore. Use the database name and credentials from the Fly `DATABASE_URL`, shown in the output of `fly postgres attach`:
   ```bash
   pg_restore --no-owner --no-acl --clean --if-exists -h localhost -p 15432 -U USER -d DBNAME helios.dump
   ```
4. Deploy, then **immediately stop the worker** so it can't pick up the waiting tasks the dump brought along:
   ```bash
   fly deploy -a YOUR_FLY_APP
   ```
   ```bash
   fly scale count worker=0 -a YOUR_FLY_APP --yes
   ```
   The `release_command` runs `manage.py migrate` before new machines start. **If your `fly.toml` has no `release_command`**, run it yourself after each deploy:
   ```bash
   fly ssh console -a YOUR_FLY_APP -C '/app/.venv/bin/python manage.py migrate --noinput'
   ```
5. Clear the copied queue on the **rehearsal database only**. These tasks belong to Heroku, which is still running and will run them itself:
   ```bash
   fly ssh console -a YOUR_FLY_APP -C '/app/.venv/bin/python manage.py shell -c "from django_tasks import TaskResultStatus; from django_tasks_db.models import DBTaskResult; print(DBTaskResult.objects.filter(status__in=[TaskResultStatus.READY, TaskResultStatus.RUNNING]).delete())"'
   ```
   Then start the worker:
   ```bash
   fly scale count web=2 worker=1 -a YOUR_FLY_APP
   ```
6. Test at `https://YOUR_FLY_APP.fly.dev`:
   - log in with each enabled auth system;
   - open an existing election and its booth (`/booth/…`) and verifier (`/verifier/…`); confirm JS/CSS loads (check the browser console for 404s or CSP errors);
   - create a **test** election, upload a small voter file, cast a ballot, and confirm it's verified (this exercises `db_worker` end to end);
   - tally the test election;
   - open `/helios/stats/` and check the task counts: nothing should stay waiting, stuck or failed;
   - redeploy (`fly deploy`) while the worker is idle and confirm it restarts cleanly;
   - check logs: `fly logs -a YOUR_FLY_APP`. Look for `DisallowedHost`, database SSL errors, and worker tracebacks.

   Email isn't configured yet, so voter-email tasks will fail. That's expected and confirms the safety net works.

The cutover restores over this copy, so don't bother cleaning up test data.

## Step 6: Schedule the queue maintenance jobs

The task table needs two recurring jobs (`INSTALL.md`, "Background Tasks"):

- `prune_db_task_results`: daily, to delete finished tasks.
- `requeue_stuck_tasks --older-than 120`: hourly, to recover tasks left "running" by a worker that died mid-task.

Fly has no Heroku Scheduler. Options:

- **Scheduled Machines.** Fly can run a Machine on an `hourly`/`daily`/`weekly`/`monthly` schedule. The Machine runs a fixed image, so re-point it at the new image after each deploy, or it runs old code.
  ```bash
  fly machine run registry.fly.io/YOUR_FLY_APP:CURRENT_TAG --schedule daily -a YOUR_FLY_APP -- /app/.venv/bin/python manage.py prune_db_task_results
  ```
- **An external scheduler** you already have, such as GitHub Actions `schedule:`, running `fly ssh console -C '…'` with a deploy token. This always runs the current release.

Whichever you pick, run each job once by hand first to check it works:

```bash
fly ssh console -a YOUR_FLY_APP -C '/app/.venv/bin/python manage.py requeue_stuck_tasks --dry-run'
```

## Step 7: Cutover

Lower your DNS TTL for `vote.example.org` to ~60s at least a day before.

1. **Add the TLS certificate on Fly ahead of time** so it's ready the moment DNS moves:
   ```bash
   fly certs add vote.example.org -a YOUR_FLY_APP
   ```
   Follow its instructions (an `_acme-challenge` CNAME lets Fly issue the cert before you switch traffic).
2. **Stop the Fly worker** so it doesn't touch the database while you restore over it:
   ```bash
   fly scale count worker=0 -a YOUR_FLY_APP --yes
   ```
3. **Freeze Heroku and drain its queue.** Maintenance mode stops new work. The Heroku worker keeps running and finishes what's queued:
   ```bash
   heroku maintenance:on -a YOUR_HEROKU_APP
   ```
   Wait until nothing is waiting or running. Maintenance mode hides the stats page, so check the counts from a shell:
   ```bash
   heroku run -a YOUR_HEROKU_APP python manage.py shell -c "from django_tasks_db.models import DBTaskResult; print(DBTaskResult.objects.ready().count(), DBTaskResult.objects.running().count())"
   ```
   When both are `0`, stop the Heroku worker:
   ```bash
   heroku ps:scale worker=0 -a YOUR_HEROKU_APP
   ```
   If the queue won't drain (for example a large email blast), you can stop anyway. Waiting tasks move with the dump and the Fly worker runs them. Only *running* tasks need care; see item 5.
4. **Final dump and restore.** Repeat Step 5 items 1–3 (capture, download, `pg_restore --clean`). **Don't** clear the queue this time: whatever is waiting now belongs to the live system.
5. **Recover tasks that were mid-run on Heroku.** Any task still marked running in the dump will never finish on its own. Check for them:
   ```bash
   fly ssh console -a YOUR_FLY_APP -C '/app/.venv/bin/python manage.py requeue_stuck_tasks --older-than 0 --dry-run'
   ```
   If it reports any, requeue them by running it again without `--dry-run`. Bulk voter emails (`voters_email`, `voters_notify`) are listed but never requeued, because rerunning one emails every voter again. For those, check which voters already got the email before resending from the election's admin page.
6. **Set the email credentials**, migrate, and start the worker:
   ```bash
   fly secrets set -a YOUR_FLY_APP MAILGUN_API_KEY='…' DEFAULT_FROM_EMAIL='…' DEFAULT_FROM_NAME='…'
   ```
   ```bash
   fly ssh console -a YOUR_FLY_APP -C '/app/.venv/bin/python manage.py migrate --noinput'
   ```
   ```bash
   fly scale count worker=1 -a YOUR_FLY_APP
   ```
7. **Switch DNS** for `vote.example.org` to the A/AAAA (or CNAME) records `fly certs show vote.example.org` gives you.
8. **Verify** once DNS resolves to Fly:
   - log in;
   - open an existing election via its stored URL;
   - check `/helios/stats/`: the waiting count should drop to zero and nothing should be stuck;
   - run `fly certs check vote.example.org`.

## Step 8: Rollback

Keep Heroku (app and database) intact for at least a couple of weeks. Leave its worker scaled to 0 and maintenance on.

To roll back:

1. Stop the Fly worker (`fly scale count worker=0`).
2. If anything was written on Fly after cutover (votes, new elections, queued emails), dump Fly's database and restore it onto Heroku (the steps in reverse, including the stuck-task check). Otherwise that data is lost.
3. Point DNS back to Heroku.
4. Run `heroku ps:scale worker=1`, then `heroku maintenance:off`.

The queue moves with the database in both directions, so there's no separate queue to reconcile. That's another reason to cut over between elections.

## Step 9: Clean up

Once you're confident:
- Delete `heroku.env` and `helios.dump`.
- Raise the DNS TTL back to normal.
- Remove any temporary `*.fly.dev` OAuth redirect URIs (or keep them for staging).
- Delete Heroku Scheduler jobs, then the Heroku app and add-ons (`heroku apps:destroy`). This is irreversible, so take one final backup first.

---

## Operating on Fly: quick reference

| Task | Heroku | Fly |
|---|---|---|
| Logs | `heroku logs -t` | `fly logs` |
| Shell | `heroku run bash` | `fly ssh console` |
| Django shell | `heroku run python manage.py shell` | `fly ssh console -C '/app/.venv/bin/python manage.py shell'` |
| Config vars | `heroku config:set K=V` | `fly secrets set K=V` (restarts machines), or `[env]` in `fly.toml` for non-secrets |
| Scale | `heroku ps:scale web=2 worker=2` | `fly scale count web=2 worker=2` |
| Bigger machines | dyno types | `fly scale vm shared-cpu-2x --memory 1024 --process-group worker` |
| Release phase | `release:` in Procfile | `[deploy] release_command` |
| Scheduled jobs | Heroku Scheduler | Scheduled Machines or an external scheduler (Step 6) |
| Queue health | `/helios/stats/` | `/helios/stats/` |
| Maintenance mode | `heroku maintenance:on` | none built in; `fly scale count web=0` or serve a static page |

**Production recommendations**
- Keep `min_machines_running = 1` (or higher) during elections; scale-to-zero means cold starts for voters.
- Each `db_worker` runs one task at a time, and several workers are safe, since each task is claimed by exactly one. Scale `worker` to 2+ so a long tally doesn't hold up vote verification and emails.
- Give the `worker` process group ≥1 GB. Tallying and bulk email run there.
- Deploys restart workers. `db_worker` finishes its current task when it receives SIGTERM, but only within `kill_timeout`. A tally that runs longer is killed mid-task and needs `requeue_stuck_tasks`. Avoid deploying during a tally.
- The database is now the single point of failure for both data and the queue. Back it up independently of Fly (e.g. scheduled `pg_dump` to object storage), especially with unmanaged Postgres.
