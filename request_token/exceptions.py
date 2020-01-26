"""
Local exceptions related to tokens.

These exceptions all inherit from the PyJWT base InvalidTokenError.

"""
from __future__ import annotations

from jwt.exceptions import InvalidTokenError


class MaxUseError(InvalidTokenError):
    """Error raised when a token has exceeded its max_use cap."""

    pass


class ScopeError(InvalidTokenError):
    """Error raised when a token scope does not match the function scope."""

    pass


class TokenNotFoundError(InvalidTokenError):
    """Error raised when a token is expected, but not found."""

    pass
