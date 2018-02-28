from os import getenv

from django.conf import settings


def _env_or_setting(key, default):
    return getenv(key) or getattr(settings, key, default)


# the name of GET argument to contain the token
JWT_QUERYSTRING_ARG = _env_or_setting('REQUEST_TOKEN_QUERYSTRING', 'rt')

# the fixed expiration check on Session tokens
JWT_SESSION_TOKEN_EXPIRY = int(_env_or_setting('REQUEST_TOKEN_EXPIRY', 10))

# Set the default 403 template value
FOUR03_TEMPLATE = _env_or_setting('REQUEST_TOKEN_403_TEMPLATE', None)

# log all InvalidTokenErrors
LOG_TOKEN_ERRORS = _env_or_setting('REQUEST_TOKEN_LOG_TOKEN_ERRORS', 'True').lower() in ('true', '1')  # noqa
