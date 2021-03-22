from django.conf import settings

# the name of GET argument to contain the token
JWT_QUERYSTRING_ARG: str = getattr(settings, "REQUEST_TOKEN_QUERYSTRING", "rt")

# the fixed expiration check on Session tokens
JWT_SESSION_TOKEN_EXPIRY: int = getattr(settings, "REQUEST_TOKEN_EXPIRY", 10)

DEFAULT_MAX_USES: int = getattr(settings, "REQUEST_TOKEN_DEFAULT_MAX_USES", 10)
