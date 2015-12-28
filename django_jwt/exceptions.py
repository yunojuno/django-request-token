# -*- coding: utf8 -*-
"""django_jwt expections.

Local exceptions related to tokens inherit from the PyJWT base
InvalidTokenError.

"""
from jwt.exceptions import InvalidTokenError


class MaxUseError(InvalidTokenError):

    """Error raised when a token has exceeded its max_use cap."""

    pass


class TargetUrlError(InvalidTokenError):

    """Error raised when a token target_url does not match the request path."""

    pass
