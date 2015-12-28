# -*- coding: utf-8 -*-
"""django_jwt decorators."""
import logging

from jwt.exceptions import InvalidTokenError, DecodeError

from django_jwt import settings
from django_jwt.models import RequestToken

logger = logging.getLogger(__name__)


def use_jwt(view_func):
    """Decorator used to exapand and verify JWT tokens.

    This function decorator is responsible for expanding the token and
    validating that it can be used - has not expired, exceeded max uses etc.

    If the token cannot be used, we don't raise an HTTP error, we rely on the
    underlying view to handle it - i.e. a request with and invalid token
    therefore behaves as if it would if the token did not exist.

    The underlying error is logged as a WARNING, so that it can be monitored.

    """
    def inner(request, *args, **kwargs):

        jwt = request.GET.get(settings.JWT_QUERYSTRING_ARG, None)
        if jwt is None:
            return view_func(request, *args, **kwargs)

        try:
            token, token_error = RequestToken.objects.get_from_jwt(jwt), None
            token.validate()
            token.validate_request(request)
        except DecodeError as ex:
            logger.warning("JWT token decode error: %s", jwt)
            token, token_error = (None, ex)
        except RequestToken.DoesNotExist as ex:
            logger.warning("JWT token does not exist: %s", jwt)
            token, token_error = (None, ex)
        except InvalidTokenError as ex:
            logger.warning("%s: %s", ex, jwt)
            token_error = ex
        finally:
            # we call the view irrespective - if the token worked we
            # will have a request.user set, else we are calling the func
            # with the existing user.
            response = view_func(request, *args, **kwargs)
            request.token = token
            request.token_error = token_error
            request.token_used = token is not None and token_error is None
            if request.token_used:
                request.token.log(request, response)

        return response

    return inner
