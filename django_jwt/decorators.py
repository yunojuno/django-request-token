# -*- coding: utf-8 -*-
"""django_jwt decorators."""
import functools
import logging

from django.http import HttpResponseForbidden

from jwt.exceptions import InvalidTokenError

from django_jwt.exceptions import ScopeError
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


def expiring_link(view_func=None, scope=None):
    """Decorator used to indicate that function supports expiring links.

    This function decorator is responsible for expanding the JWT token and
    validating that it can be used - has not expired, exceeded max uses etc.

    If the token cannot be used, we don't raise an HTTP error, we rely on the
    underlying view to handle it - i.e. a request with an invalid token
    behaves as if it would if the token did not exist, although the validation
    error raised is logged as a WARNING, so that it can be monitored.

    If an error is raised during the token validation, it is added to the
    response as `response.token_error` - this can then be intercepted in
    custom middleware should you wish to.

    For more details on decorators with optional args, see:
    https://blogs.it.ox.ac.uk/inapickle/2012/01/05/python-decorators-with-optional-arguments/

    """
    assert scope not in ('', None), "@expiring_link decorator scope cannot be empty."

    if view_func is None:
        return functools.partial(expiring_link, scope=scope)

    @functools.wraps(view_func)
    def inner(request, *args, **kwargs):

        payload = getattr(request, 'token_payload', None)
        if payload is None:
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
            request.token, request.user = token, token.user
            response = view_func(request, *args, **kwargs)
            token.log(request, response)
            return response

        except (RequestToken.DoesNotExist, InvalidTokenError) as ex:
            # this will log the exception and return a 403
            return respond_to_error(request.session.session_key, ex)

    return inner

