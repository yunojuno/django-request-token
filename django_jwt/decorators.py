# -*- coding: utf-8 -*-
"""django_jwt decorators."""
import logging

from jwt.exceptions import InvalidTokenError

from django_jwt.utils import decode
from django_jwt.models import RequestToken
from django_jwt.settings import JWT_QUERYSTRING_ARG

logger = logging.getLogger(__name__)


def expiring_link(view_func):
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

    """
    def inner(request, *args, **kwargs):

        jwt = request.GET.get(JWT_QUERYSTRING_ARG, None)
        if jwt is None:
            return view_func(request, *args, **kwargs)

        token, token_error = (None, None)

        try:
            # decoding the token uses PyJWT decode, raising InvalidTokenError -
            # NB in these cases the token is never loaded from the DB
            jwt_decoded = decode(jwt)
            token_id = jwt_decoded['jti']
            # raises standard DoesNotExist exception if not found
            token = RequestToken.objects.get(id=token_id)
            # raises MaxUseError, TargetUrlError, InvalidAudienceError -
            # these are all InvalidTokenError exceptions, but in this case
            # the token _will_ have been loaded from the db
            token.validate_request(request)
            # JWT hsa been verified, and token checks out, so set the user
            request.user = token.user
        except InvalidTokenError as ex:
            logger.warning("JWT token error: %s", ex)
            token_error = ex
        except RequestToken.DoesNotExist as ex:
            logger.warning("JWT token error: RequestToken [%s] does not exist", token_id)
            token_error = ex
        finally:
            # we call the view irrespective - if the token worked we
            # will have a new request.user set, else we are calling the func
            # with the existing user.
            request.token = token
            response = view_func(request, *args, **kwargs)
            response.token_error = token_error

            if request.token is not None and response.token_error is None:
                token.log(request, response)

        return response

    return inner
