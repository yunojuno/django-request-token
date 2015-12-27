# -*- coding: utf-8 -*-
"""django_jwt middleware for processing JWT request tokens.

If an incoming request contains a request token (as identified
by the DJANGO_JWT_AUTH_KEY), then the token is decoded, and
verified. If it's found to be valid, then the user defined
as the audience of the token is added to the request - essentially
authenticating the user on the per-request basis. This enables the
distribution of single-use URLs - e.g. for sending out in emails.

NB the authentication is only valid for a single request - it
does **not** update the session cookie, and so if the URL returns
a 3xx redirect after processing, the next request will be un-
authenticated.

"""
import logging

import jwt
from jwt.exceptions import InvalidTokenError

from django.conf import settings

logger = logging.getLogger(__name__)


def process_request(request):
    """Extract and validate JWT token from request.

    The token is passed in on the querystring (NB this is not the
    standard use case for JWT - which are usually passed in as a
    request header).

    """
    token = request.GET.get(settings.JWT_AUTH_KEY)
    if token is None:
        return

    try:
        decoded = jwt.decode(token, settings.SECRET_KEY)
    except InvalidTokenError:
        logger.exception("Invalid JWT token.")
        return
