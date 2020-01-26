from __future__ import annotations

import functools
import logging
from typing import Any, Callable, Optional

from django.http import HttpRequest, HttpResponse

from .exceptions import ScopeError, TokenNotFoundError

logger = logging.getLogger(__name__)


def _get_request_arg(*args: Any) -> Optional[HttpRequest]:
    """Extract the arg that is an HttpRequest object."""
    for arg in args:
        if isinstance(arg, HttpRequest):
            return arg
    return None


def use_request_token(
    view_func: Optional[Callable] = None,
    scope: Optional[str] = None,
    required: bool = False,
) -> Callable:
    """
    Decorate view functions that supports RequestTokens.

    This decorator is used in conjunction with RequestTokens and the
    RequestTokenMiddleware. By the time that a request has passed through the
    middleware and reached the view function, if a RequestToken exists it will
    have been decoded, and the payload added to the request as `token_payload`.

    This decorator is then used to map the `sub` JWT token claim to the function
    using the 'scope' kwarg - the scope must be provided, and must match the
    scope of the request token.

    If the 'required' kwarg is True, then the view function expects a valid token
    in all cases - and the decorator will raise TokenNotFoundError if one does
    not exist.

    Errors are trapped and returned as HttpResponseForbidden responses, with
    the original error as the `response.error` property.

    For more details on decorators with optional args, see:
    https://blogs.it.ox.ac.uk/inapickle/2012/01/05/python-decorators-with-optional-arguments/

    """
    if not scope:
        raise ValueError("Decorator scope cannot be empty.")

    if view_func is None:
        return functools.partial(use_request_token, scope=scope, required=required)

    @functools.wraps(view_func)
    def inner(*args: Any, **kwargs: Any) -> HttpResponse:
        # HACK: if this is decorating a method, then the first arg will be
        # the object (self), and not the request. In order to make this work
        # with functions and methods we need to determine where the request
        # arg is.
        request = _get_request_arg(*args)
        token = getattr(request, "token", None)
        if not view_func:
            raise ValueError("Missing view_func")

        if token is None:
            if required is True:
                raise TokenNotFoundError()
            return view_func(*args, **kwargs)

        if token.scope == scope:
            token.validate_max_uses()
            token.authenticate(request)
            response = view_func(*args, **kwargs)
            # this will only log the request here if the view function
            # returns a valid HttpResponse object - if the view function
            # raises an error, **or this decorator raises an error**, it
            # will be handled in the middleware process_exception function,
            token.log(request, response)
            return response

        raise ScopeError(
            "RequestToken scope mismatch: '%s' != '%s'" % (token.scope, scope)
        )

    return inner
