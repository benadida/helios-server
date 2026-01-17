# CLAUDE.md

This file provides guidance to Claude Code when working with the Helios Election System codebase.

## Project Overview

Helios is an end-to-end verifiable voting system that provides secure, transparent online elections with cryptographic verification. It supports multiple authentication systems (Google, Facebook, GitHub, LDAP, CAS, password, etc.) and uses homomorphic encryption for privacy-preserving vote tallying.

## Critical Instructions for Claude when preparing a PR

- always run the tests. Install everything and run the tests. Every time.

## Technology Stack

- **Python**: 3.13
- **Framework**: Django 5.2
- **Database**: PostgreSQL 9.5+
- **Task Queue**: Celery with RabbitMQ
- **Crypto**: pycryptodome
- **Package Manager**: uv

## Common Commands

```bash
# Install dependencies
uv sync

# Run development server
uv run python manage.py runserver

# Run all tests
uv run python manage.py test -v 2

# Run tests for a specific app
uv run python manage.py test helios -v 2
uv run python manage.py test helios_auth -v 2

# Run a specific test class
uv run python manage.py test helios.tests.ElectionModelTests -v 2

# Database migrations
uv run python manage.py makemigrations
uv run python manage.py migrate

# Reset database (drops and recreates)
./reset.sh

# Start Celery worker (for background tasks)
uv run celery --app helios worker --events --beat --concurrency 1
```

## Project Structure

- `helios/` - Core election system (models, views, crypto, forms)
- `helios_auth/` - Authentication system with multiple backends
- `server_ui/` - Admin web interface
- `heliosbooth/` - JavaScript voting booth interface
- `heliosverifier/` - JavaScript ballot verification interface

## Code Style Conventions

### Naming

- **Boolean fields**: Use `_p` suffix (e.g., `private_p`, `frozen_p`, `admin_p`, `featured_p`)
- **Datetime fields**: Use `_at` suffix (e.g., `created_at`, `frozen_at`, `voting_ends_at`)
- **Functions/methods**: snake_case
- **Classes**: PascalCase

### Indentation

- Use 2-space indentation throughout Python files

### Imports

```python
# Standard library
import copy, csv, datetime, uuid

# Third-party
from django.db import models, transaction
import bleach

# Local
from helios import datatypes, utils
from helios_auth.jsonfield import JSONField
```

## Key Patterns

### View Decorators

Use existing security decorators for views:

```python
from helios.security import election_view, election_admin, trustee_check

@election_view(frozen=True)
def my_view(request, election):
    pass

@election_admin()
def admin_view(request, election):
    pass
```

### Model Base Class

All domain models inherit from `HeliosModel`:

```python
class MyModel(HeliosModel):
    class Meta:
        app_label = 'helios'
```

### JSON Responses

```python
from helios.views import render_json
return render_json({'key': 'value'})
```

### Template Rendering

```python
from helios.views import render_template
return render_template(request, 'template_name', {'context': 'vars'})
```

### Database Queries

- Use `@transaction.atomic` for operations that need atomicity
- Prefer `select_related()` for foreign key joins
- Use `get_or_create()` pattern for safe creation

## Security Considerations

- Always use `check_csrf(request)` for POST handlers
- Use `bleach.clean()` for user-provided HTML (see `description_bleached` pattern)
- Never store plaintext passwords; use the auth system's hashing
- Check permissions with `user_can_admin_election()` and similar helpers

## Configuration

Settings use environment variables with defaults:

```python
from settings import get_from_env
MY_SETTING = get_from_env('MY_SETTING', 'default_value')
```

Key environment variables: `DEBUG`, `SECRET_KEY`, `DATABASE_URL`, `CELERY_BROKER_URL`, `AUTH_ENABLED_AUTH_SYSTEMS`

## Testing

- Tests use Django's TestCase with django-webtest
- Fixtures are in `helios/fixtures/`
- Test classes: `ElectionModelTests`, `VoterModelTests`, `ElectionBlackboxTests`, etc.
