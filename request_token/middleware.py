from __future__ import annotations

import json
import logging
from typing import Callable, Optional

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseForbidden
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.template import loader
from jwt.exceptions import InvalidTokenError

from .models import RequestToken
from .settings import FOUR03_TEMPLATE, JWT_QUERYSTRING_ARG, JWT_SESSION_CLAIMS_KEY

logger = logging.getLogger(__name__)


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


def get_request_jwt(request: HttpRequest) -> str:
    """Extract JWT token string from the incoming request."""
    if request.method not in ("GET", "POST"):
        return ""

    def try_get() -> Optional[str]:
        return request.GET.get(JWT_QUERYSTRING_ARG, "")

    def try_post() -> Optional[str]:
        if request.META.get("CONTENT_TYPE") == "application/json":
            return json.loads(request.body).get(JWT_QUERYSTRING_ARG, "")
        return request.POST.get(JWT_QUERYSTRING_ARG, "")

    return try_get() or try_post() or ""


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
        if jwt := get_request_jwt(request):
            request.token = RequestToken.objects.from_jwt(jwt)
        else:
            request.token = None
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


class SessionTokenMiddleware:
    """Manage tokens stashed in request.session."""

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        Handle tokens stashed in the session if not on the request.

        This middleware builds on the RequestTokenMiddleware which sets
        the `request.token` attribute. If this is None, then we have no
        new token from the request itself, but we may have an older token
        stashed in the `request.session` dict. If this is the case, we
        "rehydrate" it, add to the `request.token`, and decrement its
        `ttl` attribute. Once the `token.ttl` reaches zero, we eject it
        from the session so that it is no longer available.

        """
        if not hasattr(request, "session"):
            raise ImproperlyConfigured(
                "Request has no 'session' attribute, please ensure that Django "
                "session middleware is installed."
            )

        if not hasattr(request, "token"):
            raise ImproperlyConfigured(
                "Request has no 'token' attribute, please ensure that "
                "RequestTokenMiddleware is installed."
            )

        # popping from the session ensures that the session claims will only
        # be restored if there is a valid token associated with them.
        session_claims = request.session.pop(JWT_SESSION_CLAIMS_KEY, {})
        if session_claims and not request.token:
            # we don't have a new token on the request, but we do have
            # an old one stashed. In this scenario we rehydrate it.
            # NB The rehydrate method will return None if the token has
            # reached its TTL.
            request.token = RequestToken.objects.from_claims(session_claims)

        if request.token:
            request.token.decrement()
            request.session[JWT_SESSION_CLAIMS_KEY] = request.token.claims

        return self.get_response(request)
