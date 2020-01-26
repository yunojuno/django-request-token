from __future__ import annotations

from typing import Dict

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest
from django.utils.functional import SimpleLazyObject


def request_token(request: HttpRequest) -> Dict[str, SimpleLazyObject]:
    """Add a request_token to template context (if found on the request)."""

    def _get_val() -> str:
        try:
            return request.token.jwt()
        except AttributeError:
            raise ImproperlyConfigured(
                "Request has no 'token' attribute - "
                "is RequestTokenMiddleware installed?"
            )

    return {"request_token": SimpleLazyObject(_get_val)}
