# Dockerfile for Fly.io deployment
# Also usable for any Docker-based deployment.
# Heroku deployment continues to use the Procfile and does not use this file.

FROM python:3.13-slim AS base

# Install system dependencies required by python-ldap and psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libldap2-dev \
    libsasl2-dev \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first (layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Default port (Fly.io sets PORT=8080 by default)
ENV PORT=8080

EXPOSE 8080

# Run gunicorn via uv so it picks up the virtual environment
CMD ["sh", "-c", "uv run gunicorn wsgi:application -b 0.0.0.0:$PORT -w 4"]
