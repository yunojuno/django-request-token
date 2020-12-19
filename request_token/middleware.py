from __future__ import annotations
from datetime import datetime

import json
import logging
from request_token.exceptions import TokenExpired
from typing import Callable, Optional
from django.contrib.sessions.backends.base import SessionBase
from django.core import exceptions

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseForbidden
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.template import loader
from django.utils.timezone import now as tz_now

from jwt.exceptions import InvalidAudienceError, InvalidTokenError

from .models import RequestToken
from .settings import FOUR03_TEMPLATE, JWT_QUERYSTRING_ARG, JWT_SESSION_TOKEN_KEY
from .utils import decode, to_jwt, to_seconds

logger = logging.getLogger(__name__)


def has_expired(claims: dict) -> bool:
    """Return True if the "exp" claim has expired."""
    if "exp" not in claims:
        return True
    return to_seconds(tz_now()) < claims["exp"]


def get_token_from_jwt(jwt: str) -> Optional[RequestToken]:
    """
    Decode JWT and fetch associated RequestToken object.

    In the event of an error we log it, but then let the request
    continue - as the fact that the token cannot be decoded, or
    no longer exists, may not invalidate the request itself.
    """
    try:
        payload = decode(jwt)
        token = RequestToken.objects.get(id=payload["jti"])
        token.validate_expiry()
    except TokenExpired:
        logger.exception("RequestToken has expired: %s", jwt)
    except InvalidTokenError:
        logger.exception("RequestToken cannot be decoded: %s", jwt)
    except RequestToken.DoesNotExist:
        logger.exception("RequestToken no longer exists: %s", jwt)
    return None


def get_request_jwt(request: HttpRequest) -> str:
    """Extract JWT token string from the incoming request."""
    if request.method not in ("GET", "POST"):
        return None

    def try_get() -> Optional[str]:
        return request.GET.get(JWT_QUERYSTRING_ARG)

    def try_post() -> Optional[str]:
        if request.META.get("CONTENT_TYPE") == "application/json":
            return json.loads(request.body).get(JWT_QUERYSTRING_ARG)
        return request.POST.get(JWT_QUERYSTRING_ARG)

    return try_get() or try_post() or ""


def get_session_jwt(session: SessionBase) -> str:
    """
    Fetch JWT from session (and validate expiry).

    If the token is in the session it may have expired, in which
    case we just ignore it. It won't be added to the request, so
    won't have any functional impact, and will be ejected when
    the session expires or a new request token is found.

    """
    claims = session.get(JWT_SESSION_TOKEN_KEY)
    if not claims:
        return ""
    if has_expired(claims):
        return ""
    return to_jwt(claims)


def get_token(request: HttpRequest) -> Optional[RequestToken]:
    """Return first valid token found in the request or the session."""
    jwt = get_request_jwt(request) or get_session_jwt(request.session)
    if jwt:
        return get_token_from_jwt(jwt)
    return None


def set_user(request: HttpRequest, token: RequestToken) -> None:
    """
    Set the request.user for REQUEST tokens.

    This method encapsulates the request handling - if the token
    has a user assigned, then this will be added to the request.

    """
    if request.user.is_authenticated and request.user != token.user:
        raise InvalidAudienceError(
            f"{token!r} audience mismatch: {request.user.pk} != {token.user.pk}"
        )
    request.user = token.user


def set_token(request: HttpRequest, token: RequestToken) -> None:
    """Store token on the request and session objects."""
    request.token = token
    # stashing the token ensures that it will be picked up on
    # the next request.
    if token.stash:
        request.session[JWT_SESSION_TOKEN_KEY] = token.claims


class RequestTokenMiddleware:
    """
    Extract and verify request tokens from incoming GET requests.

    This middleware is used to perform initial JWT verfication of
    link tokens.

    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:  # noqa: C901
        """
        Add RequestToken to request object if a valid token is found.

        This middleware supports a range of options for supplying the
        JWT - it can be in the request querystring (default), the request
        POST (via form or json), or retrived from the session if stashed
        there from a previous request.

        If a token is found, it is added as `request.token`, and stashed
        in the session (if `token.stash == True`).

        For LoginMode.REQUEST tokens it will also update the `request.user`
        attribute.

        """
        if not hasattr(request, "session"):
            raise ImproperlyConfigured(
                "Request has no session attribute, please ensure that Django "
                "session middleware is installed."
            )
        if not hasattr(request, "user"):
            raise ImproperlyConfigured(
                "Request has no user attribute, please ensure that Django "
                "authentication middleware is installed."
            )

        token = get_token(request)
        if not token:
            return self.get_response(request)

        if token.login_mode == RequestToken.LoginMode.REQUEST:
            set_user(request, token)

        set_token(request, token)
        return self.get_response(request)

    def process_exception(
        self, request: HttpRequest, exception: Exception
    ) -> HttpResponse:
        """Handle all InvalidTokenErrors."""
        if isinstance(exception, InvalidTokenError):
            logger.exception("JWT request token error")
            response = _403(request, exception)
            if getattr(request, "token", None):
                request.token.log(request, response, error=exception)
            return response


def _403(request: HttpRequest, exception: Exception) -> HttpResponseForbidden:
    """Render HttpResponseForbidden for exception."""
    if FOUR03_TEMPLATE:
        html = loader.render_to_string(
            template_name=FOUR03_TEMPLATE,
            context={"token_error": str(exception), "exception": exception},
            request=request,
        )
        return HttpResponseForbidden(html, reason=str(exception))
    return HttpResponseForbidden(reason=str(exception))
