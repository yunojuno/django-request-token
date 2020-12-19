from os import getenv
from typing import Any, Optional

from django.conf import settings


def _env_or_setting(key: str, default: Any) -> Any:
    return getenv(key) or getattr(settings, key, default)


# the name of GET argument to contain the token
JWT_QUERYSTRING_ARG: str = _env_or_setting("REQUEST_TOKEN_QUERYSTRING", "rt")

# the fixed expiration check on Session tokens
JWT_SESSION_TOKEN_KEY: str = _env_or_setting("REQUEST_TOKEN_SESSION_KEY", "rt:session")

# the fixed expiration check on Session tokens
JWT_SESSION_TOKEN_EXPIRY: int = int(_env_or_setting("REQUEST_TOKEN_EXPIRY", 10))

# Set the default 403 template value
FOUR03_TEMPLATE: Optional[str] = _env_or_setting("REQUEST_TOKEN_403_TEMPLATE", None)

# log all InvalidTokenErrors
LOG_TOKEN_ERRORS: bool = _env_or_setting(
    "REQUEST_TOKEN_LOG_TOKEN_ERRORS", "True"
).lower() in (
    "true",
    "1",
)  # noqa


DEFAULT_MAX_USES: int = int(_env_or_setting("REQUEST_TOKEN_DEFAULT_MAX_USES", 10))
