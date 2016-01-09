# -*- coding: utf-8 -*-
"""request_token decorators."""
import functools
import logging

from django.http import HttpResponseForbidden

from jwt.exceptions import InvalidTokenError

from request_token.exceptions import ScopeError, TokenNotFoundError

logger = logging.getLogger(__name__)


def respond_to_error(session_key, error):
    """Log request error and generate 403 response."""
    logger.warning(
        "JWT token error in session '%s': %s",
        session_key, error
    )
    response = HttpResponseForbidden("Invalid URL token (code: %s)" % session_key)
    response.error = error
    return response


def use_request_token(view_func=None, scope=None, required=False):
    """Decorator used to indicate that a view function supports RequestTokens.

    This decorator is used in conjunction with RequestTokens and the
    RequestTokenMiddleware. By the time that a request has passed through the
    middleware and reached the view function, if a RequestToken exists it will
    have been decoded, and the payload added to the request as `token_payload`.

    This decorator is then used to map the `sub` JWT token claim to the function
    using the 'scope' kwarg - the scope must be provided, and must match the
    scope of the request token.

    Once we have verified the scope match, we then fetch the RequestToken from
    the DB, and validate it against the max use count, and the request user.

    If the RequestToken specifies a User, then the incoming request must be
    either unauthenticated, or authenticated by the same user. If it is
    unauthenticated, then this decorator will swap in the user as the request.user
    so that the view function has the user it expects.


    If the 'required' kwarg is True, then the view function expects a valid token
    in all cases - and the decorator will raise TokenNotFoundError if one does
    not exist.

    Errors are trapped and returned as HttpResponseForbidden responses, with
    the original error as the `response.error` property.

    For more details on decorators with optional args, see:
    https://blogs.it.ox.ac.uk/inapickle/2012/01/05/python-decorators-with-optional-arguments/

    """
    assert scope not in ('', None), "Decorator scope cannot be empty."

    if view_func is None:
        return functools.partial(use_request_token, scope=scope, required=required)

    @functools.wraps(view_func)
    def inner(request, *args, **kwargs):

        token = getattr(request, 'token', None)
        try:
            if token is None:
                if required is True:
                    raise TokenNotFoundError()
                else:
                    return view_func(request, *args, **kwargs)
            else:
                if token.scope == scope:
                    response = view_func(request, *args, **kwargs)
                    token.log(request, response)
                    return response
                else:
                    raise ScopeError(
                        "RequestToken scope mismatch: '%s' != '%s'" %
                        (token.scope, scope)
                    )

        except InvalidTokenError as ex:
            # this will log the exception and return a 403
            return respond_to_error(request.session.session_key, ex)

    return inner
