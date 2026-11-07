# Migrating a Helios deployment from Heroku to Fly.io

This guide moves an existing Helios server, with its database and live elections, from Heroku to Fly.io with a short maintenance window and a rollback path. New installs can skip to [Step 3](#step-3-create-the-fly-app).

It assumes the Fly support files from benadida/helios-server#482 (`Dockerfile`, `fly.toml`, `.dockerignore`), **including the fixes from that PR's review**:

- a `[deploy] release_command` that runs migrations;
- `DEBUG = "0"` pinned in `[env]`;
- process commands that call gunicorn/celery directly instead of through `uv run`.

If your copy of `fly.toml` doesn't have these, apply them first. The notes in each step say what breaks otherwise.

> Fly's CLI and products change often. Check each `fly` command against `fly <command> --help` and the current Fly docs before running it.

---

## Before you start: three rules

1. **Don't migrate while an election is open for voting.** Pick a window with no election between "freeze" and "tally". Ballots cast on Heroku after the final database dump would be lost.
2. **Keep the same public URL.** Every election stores its `cast_url`, built from `SECURE_URL_HOST` at creation time. If voters reach Helios at `vote.example.org` today, they must reach it at `vote.example.org` on Fly too. You move the **domain**, not the URL. If you currently use `yourapp.herokuapp.com` directly, existing elections' links stay tied to Heroku. Either keep Heroku running until those elections are archived, or accept that their stored URLs will point at the old host.
3. **Copy secrets exactly, especially `SECRET_KEY` and `EMAIL_OPTOUT_SECRET`.** A new `SECRET_KEY` logs everyone out and invalidates in-flight signed tokens. A new `EMAIL_OPTOUT_SECRET` breaks every opt-out/opt-in link already sent to voters.

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

`heroku.env` contains secrets. Keep it out of the repo (it's matched by neither `.gitignore` nor `.dockerignore` unless you name it `env.sh`), and delete it when you're done.

Record:
- **Postgres version** (from `pg:info`). Create the Fly database on the same major version.
- **Celery broker**, usually `CLOUDAMQP_URL` or `CELERY_BROKER_URL` from an AMQP add-on.
- **Email provider** vars (`MAILGUN_API_KEY`, or `EMAIL_HOST`/`EMAIL_HOST_USER`/…, or `EMAIL_USE_AWS` + AWS keys).
- **Auth provider** vars (`GOOGLE_CLIENT_ID`, `GH_CLIENT_ID`, `AUTH_ENABLED_SYSTEMS`, …).
- `URL_HOST`, `SECURE_URL_HOST`, `ALLOWED_HOSTS`, `ROLLBAR_ACCESS_TOKEN`, and site branding vars.

## Step 2: Decide on the database and broker

**Database.** Two options on Fly:

| Option | `DATABASE_SSL_REQUIRE` | Notes |
|---|---|---|
| Fly Managed Postgres | `1` (default) | Fly operates backups and failover. Recommended for production. |
| `fly postgres create` (unmanaged) | `0` | You operate it. The URL from `fly postgres attach` uses the private network without TLS. |
| Keep an external DB (e.g. stay on Heroku Postgres, RDS) | `1` | Simplest cutover, but adds cross-provider latency to every query. |

`settings.py` reads `DATABASE_SSL_REQUIRE` and defaults to `1`, which forces `sslmode=require`. Set it to `0` **only** for a database reached over Fly's private network without TLS. Otherwise connections fail with an SSL error.

**Celery broker (required).** Casting a ballot queues a Celery task, so Helios **can't accept votes without a reachable broker**. Pick one:

- **Keep your existing AMQP broker** (e.g. CloudAMQP). Copy its URL into `CELERY_BROKER_URL`. No code changes needed. This is the easiest path.
- **Redis/Upstash.** Requires adding `celery[redis]` to `pyproject.toml` (not currently a dependency), then `CELERY_BROKER_URL=rediss://…`.
- **No broker** (small/test installs only): `CELERY_TASK_ALWAYS_EAGER=1` runs tasks inside the web request. Tallies and bulk emails will then hit request timeouts on larger elections.

## Step 3: Create the Fly app

```bash
fly auth login
```
```bash
fly launch --no-deploy --copy-config --name YOUR_FLY_APP
```

This keeps the repo's `fly.toml` but rewrites `app = …`. Check `primary_region`; put it near your database and voters.

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
  CELERY_BROKER_URL='amqps://…' \
  URL_HOST='https://vote.example.org' \
  SECURE_URL_HOST='https://vote.example.org' \
  ALLOWED_HOSTS='vote.example.org,YOUR_FLY_APP.fly.dev'
```

Then email, auth, and monitoring vars, as applicable:

```bash
fly secrets set --stage -a YOUR_FLY_APP \
  MAILGUN_API_KEY='…' DEFAULT_FROM_EMAIL='…' DEFAULT_FROM_NAME='…' \
  GOOGLE_CLIENT_ID='…' GOOGLE_CLIENT_SECRET='…' \
  ROLLBAR_ACCESS_TOKEN='…'
```

If you're on unmanaged Fly Postgres, set this one too:

```bash
fly secrets set --stage -a YOUR_FLY_APP DATABASE_SSL_REQUIRE=0
```

`--stage` stores the secrets without restarting anything (there's nothing deployed yet).

Notes:
- `DEBUG`, `SSL`, and `HSTS` should be in `fly.toml` `[env]` (`DEBUG="0"`, `SSL="1"`, `HSTS="1"`). If they aren't, set them as secrets. **Never deploy with `DEBUG` unset**: it defaults to on, which enables the `devlogin` auth system and lets anyone log in as any user.
- `ALLOWED_HOSTS` must include the `.fly.dev` hostname so you can test before DNS moves.
- Don't copy Heroku-only vars (`DATABASE_URL` from Heroku, `PORT`, `HEROKU_*`, `CLOUDAMQP_*` duplicates).
- OAuth providers (Google, GitHub, GitLab, Facebook): redirect URIs are based on `URL_HOST`. Since the host isn't changing, nothing needs updating. To test logins on `*.fly.dev` before cutover, temporarily add that redirect URI in each provider's console.

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
3. Restore. Use the database name and credentials from the Fly `DATABASE_URL` (`fly ssh console -a YOUR_FLY_APP -C 'printenv DATABASE_URL'` after the first deploy, or the output of `attach`):
   ```bash
   pg_restore --no-owner --no-acl --clean --if-exists -h localhost -p 15432 -U USER -d DBNAME helios.dump
   ```
4. Deploy:
   ```bash
   fly deploy -a YOUR_FLY_APP
   ```
   The `release_command` runs `manage.py migrate` before new machines start. **If your `fly.toml` has no `release_command`**, run it yourself after each deploy:
   ```bash
   fly ssh console -a YOUR_FLY_APP -C '/app/.venv/bin/python manage.py migrate --noinput'
   ```
5. Make sure exactly one worker is running. It runs Celery beat, so don't run two:
   ```bash
   fly scale count web=2 worker=1 -a YOUR_FLY_APP
   ```
6. Test at `https://YOUR_FLY_APP.fly.dev`:
   - log in with each enabled auth system;
   - open an existing election and its booth (`/booth/…`) and verifier (`/verifier/…`); confirm JS/CSS loads (check the browser console for 404s or CSP errors);
   - create a **test** election, upload a small voter file, cast a ballot, and confirm it's verified (this exercises the worker and broker);
   - send a test voter email;
   - tally the test election.
   - Check logs: `fly logs -a YOUR_FLY_APP`. Look for broker connection errors in the worker and for `DisallowedHost`.

7. Delete the test election when done, or restore again at cutover (the next step does that).

## Step 6: Cutover

Lower your DNS TTL for `vote.example.org` to ~60s at least a day before.

1. **Add the TLS certificate on Fly ahead of time** so it's ready the moment DNS moves:
   ```bash
   fly certs add vote.example.org -a YOUR_FLY_APP
   ```
   Follow its instructions (an `_acme-challenge` CNAME lets Fly issue the cert before you switch traffic).
2. **Freeze Heroku.** Stop new work first, then let the queue drain:
   ```bash
   heroku maintenance:on -a YOUR_HEROKU_APP
   ```
   Watch the worker log until queued tasks finish (`heroku logs -t -a YOUR_HEROKU_APP --dyno worker`), then:
   ```bash
   heroku ps:scale worker=0 -a YOUR_HEROKU_APP
   ```
   If Heroku and Fly share the same broker, **stop the Fly worker too** until the restore is done (`fly scale count worker=0`), so it doesn't process Heroku's tasks against the wrong database.
3. **Final dump and restore.** Repeat Step 5 items 1–3 (capture, download, `pg_restore --clean`).
4. **Migrate and start the worker on Fly:**
   ```bash
   fly ssh console -a YOUR_FLY_APP -C '/app/.venv/bin/python manage.py migrate --noinput'
   ```
   ```bash
   fly scale count worker=1 -a YOUR_FLY_APP
   ```
5. **Switch DNS** for `vote.example.org` to the A/AAAA (or CNAME) records `fly certs show vote.example.org` gives you.
6. **Verify** once DNS resolves to Fly: log in, open an existing election via its stored URL, and check `fly certs check vote.example.org`.

## Step 7: Rollback

Keep Heroku (app, database, broker) intact for at least a couple of weeks.

To roll back: point DNS back to Heroku, `heroku ps:scale worker=1`, `heroku maintenance:off`. **Any data written on Fly after cutover is lost** unless you dump Fly's database and restore it onto Heroku first (the same steps in reverse). That's another reason to cut over between elections.

## Step 8: Clean up

Once you're confident:
- Delete `heroku.env` and `helios.dump`.
- Raise the DNS TTL back to normal.
- Remove any temporary `*.fly.dev` OAuth redirect URIs (or keep them for staging).
- Downgrade, then delete, the Heroku app and add-ons (`heroku apps:destroy`). This is irreversible, so take one final backup first.

---

## Operating on Fly: quick reference

| Task | Heroku | Fly |
|---|---|---|
| Logs | `heroku logs -t` | `fly logs` |
| Shell | `heroku run bash` | `fly ssh console` |
| Django shell | `heroku run python manage.py shell` | `fly ssh console -C '/app/.venv/bin/python manage.py shell'` |
| Config vars | `heroku config:set K=V` | `fly secrets set K=V` (restarts machines), or `[env]` in `fly.toml` for non-secrets |
| Scale | `heroku ps:scale web=2` | `fly scale count web=2` |
| Bigger machines | dyno types | `fly scale vm shared-cpu-2x --memory 1024 --process-group worker` |
| Release phase | `release:` in Procfile | `[deploy] release_command` |
| Maintenance mode | `heroku maintenance:on` | none built in; `fly scale count web=0` or serve a static page |

**Production recommendations**
- Keep `min_machines_running = 1` (or higher) during elections; scale-to-zero means cold starts for voters.
- Give the `worker` process group ≥1 GB. Tallying and bulk email run there.
- Keep `worker` at exactly one machine while it runs `--beat`.
- Back up the database independently of Fly (e.g. scheduled `pg_dump` to object storage), especially with unmanaged Postgres.
