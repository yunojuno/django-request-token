# -*- coding: utf-8 -*-
from os import getenv

from django.conf import settings

# the name of GET argument to contain the token
JWT_QUERYSTRING_ARG = (
    getenv('REQUEST_TOKEN_QUERYSTRING') or
    getattr(settings, 'REQUEST_TOKEN_QUERYSTRING', 'rt')
)

# the fixed expiration check on Session tokens
JWT_SESSION_TOKEN_EXPIRY = int(
    getenv('REQUEST_TOKEN_EXPIRY') or
    getattr(settings, 'REQUEST_TOKEN_EXPIRY', 10)
)

# Set the default 403 template value
FOUR03_TEMPLATE = (
    getenv('REQUEST_TOKEN_403_TEMPLATE') or
    getattr(settings, 'REQUEST_TOKEN_403_TEMPLATE', None)
)
