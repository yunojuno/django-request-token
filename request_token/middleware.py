from __future__ import annotations
from datetime import datetime

import json
import logging
from typing import Callable, Optional
from django.contrib.sessions.backends.base import SessionBase

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
    """Decode JWT and fetch associated RequestToken object."""
    # in the event of an error we log it, but then let the request
    # continue - as the fact that the token cannot be decoded, or
    # no longer exists, may not invalidate the request itself.
    try:
        payload = decode(jwt)
        return RequestToken.objects.get(id=payload["jti"])
    except InvalidTokenError:
        logger.exception("RequestToken cannot be decoded: %s", jwt)
    except RequestToken.DoesNotExist:
        logger.exception("RequestToken no longer exists: %s", jwt)
    return None


def get_request_token(request: HttpRequest) -> Optional[RequestToken]:
    """Extract JWT token string from the incoming request."""
    if request.method not in ("GET", "POST"):
        return None

    def try_get() -> Optional[str]:
        return request.GET.get(JWT_QUERYSTRING_ARG)

    def try_post() -> Optional[str]:
        if request.META.get("CONTENT_TYPE") == "application/json":
            return json.loads(request.body).get(JWT_QUERYSTRING_ARG)
        return request.POST.get(JWT_QUERYSTRING_ARG)

    jwt = try_get() or try_post()
    if not jwt:
        return None

    return get_token_from_jwt(jwt)


def get_session_token(session: SessionBase) -> Optional[RequestToken]:
    """
    Fetch token from session and validate expiry.

    If the token is in the session it may have expired, in which
    case we just ignore it. It won't be added to the request, so
    won't have any functional impact, and will be ejected when
    the session expires or a new request token is found.

    """
    claims = session.get(JWT_SESSION_TOKEN_KEY)
    if not claims:
        return None
    if has_expired(claims):
        return None
    return get_token_from_jwt(to_jwt(claims))


def get_token(request: HttpRequest) -> Optional[RequestToken]:
    """Return first valid token found in the request or the session."""
    return get_request_token(request) or get_session_token(request.session)


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
        Verify JWT request querystring arg.

        If a token is found (using JWT_QUERYSTRING_ARG), then it is decoded,
        which verifies the signature and expiry dates, and raises a 403 if
        the token is invalid.

        The decoded payload is then added to the request as the `token_payload`
        property - allowing it to be interrogated by the view function
        decorator when it gets there.

        We don't substitute in the user at this point, as we are not making
        any assumptions about the request path at this point - it's not until
        we get to the view function that we know where we are heading - at
        which point we verify that the scope matches, and only then do we
        use the token user.

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
