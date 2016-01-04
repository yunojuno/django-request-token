# -*- coding: utf-8 -*-
"""django_jwt settings."""
from django.conf import settings

# the name of GET argument to contain the token
JWT_QUERYSTRING_ARG = getattr(settings, 'JWT_QUERYSTRING_ARG', 'token')

# the fixed expiration check on Session tokens
JWT_SESSION_TOKEN_EXPIRY = int(getattr(settings, 'JWT_SESSION_TOKEN_EXPIRY', 1))
