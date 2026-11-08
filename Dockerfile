# Container image for Fly.io (also works for any Docker host).
# Heroku keeps using the Procfile and buildpacks and ignores this file.

FROM python:3.13-slim

# python-ldap is built from source: it needs the LDAP/SASL headers and a compiler.
# The -dev packages also pull in the runtime libraries.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libldap2-dev \
    libsasl2-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /bin/uv

WORKDIR /app

# install dependencies first so code changes don't invalidate this layer
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

# run the virtualenv's binaries directly; `uv run` would re-sync at startup
# and install the dev dependency group
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Helios stores uploads in the database, so the app never writes to disk
RUN useradd --system --no-create-home helios
USER helios

EXPOSE 8080

# fly.toml overrides this per process; this default runs the web server
CMD ["sh", "-c", "exec gunicorn wsgi:application -b 0.0.0.0:${PORT} -w 4"]
