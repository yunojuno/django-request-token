# -*- coding: utf-8 -*-
"""request_token settings."""
from django.conf import settings

# the name of GET argument to contain the token
JWT_QUERYSTRING_ARG = getattr(settings, 'JWT_QUERYSTRING_ARG', 'rt')

# the fixed expiration check on Session tokens
JWT_SESSION_TOKEN_EXPIRY = int(getattr(settings, 'JWT_SESSION_TOKEN_EXPIRY', 10))

# Set the default 403 template value
FOUR03_TEMPLATE = getattr(settings, 'FOUR03_TEMPLATE', None)
