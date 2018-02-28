import logging

from django.http import HttpResponseForbidden, HttpResponseNotAllowed
from django.template import loader

from jwt.exceptions import InvalidTokenError

from .models import RequestToken
from .settings import JWT_QUERYSTRING_ARG, FOUR03_TEMPLATE
from .utils import decode

logger = logging.getLogger(__name__)


class RequestTokenMiddleware:

    """
    Extract and verify request tokens from incoming GET requests.

    This middleware is used to perform initial JWT verfication of
    link tokens.

    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """Verify JWT request querystring arg.

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
        assert hasattr(request, 'session'), (
            "Request has no session attribute, please ensure that Django "
            "session middleware is installed."
        )
        assert hasattr(request, 'user'), (
            "Request has no user attribute, please ensure that Django "
            "authentication middleware is installed."
        )

        token = request.GET.get(JWT_QUERYSTRING_ARG)

        if token is None:
            return self.get_response(request)

        if request.method != 'GET':
            return HttpResponseNotAllowed(['GET'])

        # in the event of an error we log it, but then let the request
        # continue - as the fact that the token cannot be decoded, or
        # no longer exists, may not invalidate the request itself.
        try:
            payload = decode(token)
            request.token = RequestToken.objects.get(id=payload['jti'])
        except RequestToken.DoesNotExist:
            request.token = None
            logger.exception("RequestToken no longer exists: %s", payload['jti'])
        except InvalidTokenError:
            request.token = None
            logger.exception("RequestToken cannot be decoded: %s", token)

        return self.get_response(request)

    def process_exception(self, request, exception):
        """Handle all InvalidTokenErrors."""
        if isinstance(exception, InvalidTokenError):
            logger.exception("JWT request token error")
            response = _403(exception)
            if getattr(request, 'token', None):
                request.token.log(request, response, error=exception)
            return response


def _403(exception):
    """Render HttpResponseForbidden for exception."""
    if FOUR03_TEMPLATE:
        html = loader.render_to_string(
            FOUR03_TEMPLATE,
            context={'token_error': str(exception)}
        )
        return HttpResponseForbidden(html, reason=str(exception))
    else:
        return HttpResponseForbidden(reason=str(exception))
