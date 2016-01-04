# -*- coding: utf-8 -*-
"""django_jwt decorators."""
import functools
import logging

from django.http import HttpResponseForbidden

from jwt.exceptions import InvalidTokenError

from django_jwt.exceptions import ScopeError, TokenNotFoundError
from django_jwt.models import RequestToken

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
    assert scope not in ('', None), "@expiring_link decorator scope cannot be empty."

    if view_func is None:
        return functools.partial(use_request_token, scope=scope, required=required)

    @functools.wraps(view_func)
    def inner(request, *args, **kwargs):

        payload = getattr(request, 'token_payload', None)
        if payload is None:
            if required is True:
                return respond_to_error(request.session.session_key, TokenNotFoundError())
            else:
                return view_func(request, *args, **kwargs)

        try:
            subject = payload['sub']
            if subject != scope:
                raise ScopeError(
                    "RequestToken scope mismatch: '%s' != '%s'" %
                    (subject, scope)
                )
            # raises standard DoesNotExist exception if not found
            token_id = payload['jti']
            token = RequestToken.objects.get(id=token_id)
            # raises MaxUseError, InvalidAudienceError
            token.validate_request(request)
            # JWT hsa been verified, and token checks out, so set the user
            request.token = token
            if token.user is not None:
                request.user = token.user
            response = view_func(request, *args, **kwargs)
            token.log(request, response)
            return response

        except (RequestToken.DoesNotExist, InvalidTokenError) as ex:
            # this will log the exception and return a 403
            return respond_to_error(request.session.session_key, ex)

    return inner
