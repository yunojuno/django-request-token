# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

django-request-token is a Django app that provides JWT-backed tokens for managing one-time/expiring URL access. It supports three login modes: NONE (public link), REQUEST (single-request auth), and SESSION (full session login). Built on PyJWT, it uses Django's SECRET_KEY for signing.

**Requirements:** Python 3.12+, Django 5.2–6.0, PyJWT 2.11+

## Common Commands

### Testing
```bash
# Run full test suite
pytest --cov=request_token --verbose tests/

# Run a single test file
pytest tests/test_models.py -v

# Run a single test
pytest tests/test_models.py::RequestTokenTests::test_jwt -v

# Run via tox (full matrix: Django 5.2/6.0 × Python 3.12/3.13)
tox
```

### Linting & Formatting
```bash
ruff check request_token        # lint
ruff format --check request_token  # format check
ruff format request_token       # auto-format
mypy request_token              # type check
```

### Django Checks
```bash
python manage.py check --fail-level WARNING
python manage.py makemigrations --dry-run --check --verbosity 3
```

## Architecture

### Core Flow
1. **Middleware** (`middleware.py`) extracts JWT from querystring (`?rt=`), POST form, or AJAX JSON body, decodes it, fetches the `RequestToken` by `jti` claim, and attaches it to `request.token`
2. **Decorator** `@use_request_token(scope)` on views validates scope, enforces max_uses, optionally authenticates the user, and logs usage
3. **Models** — `RequestToken` stores token config (scope, login_mode, expiration, max_uses, user) and generates JWTs; `RequestTokenLog` is the audit trail

### Key Modules
- **`models.py`** — `RequestToken` (JWT generation, validation, authentication) and `RequestTokenLog` (audit)
- **`middleware.py`** — `RequestTokenMiddleware` (JWT extraction & decoding, adds `request.token`)
- **`decorators.py`** — `@use_request_token(scope, required, log)` for view-level token enforcement
- **`utils.py`** — JWT encode/decode wrappers, format validation (`is_jwt`), claim checking
- **`settings.py`** — App settings: `JWT_QUERYSTRING_ARG`, `JWT_SESSION_TOKEN_EXPIRY`, `DEFAULT_MAX_USES`, `DISABLE_LOGS`
- **`exceptions.py`** — `MaxUseError`, `ScopeError`, `TokenNotFoundError` (all inherit `InvalidTokenError`)

### Configuration
App settings are accessed via `request_token.settings` and can be overridden in Django settings with the `REQUEST_TOKEN_` prefix (e.g., `REQUEST_TOKEN_DISABLE_LOGS`).

## Code Style
- **Ruff** for linting and formatting (line length 88, double quotes)
- **mypy** with strict optional and untyped defs checking (disabled for admin, migrations, tests)
- Tests use `django.test.TestCase` and `unittest.mock`; security/assert lint rules relaxed in tests
