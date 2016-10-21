# -*- coding: utf-8 -*-
"""request_token middleware."""
import logging

from django.http import HttpResponseForbidden, HttpResponseNotAllowed

from jwt.exceptions import InvalidTokenError

from request_token.models import RequestToken
from request_token.settings import JWT_QUERYSTRING_ARG
from request_token.utils import decode

## For rendering  a custom 403-page
from django.template import loader 
from request_token.settings import FOUR03_TEMPLATE

logger = logging.getLogger(__name__)


class RequestTokenMiddleware(object):

    """Extract and verify request tokens from incoming GET requests.

    This middleware is used to perform initial JWT verfication of
    link tokens.

    """

    def process_request(self, request):
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
            return

        if request.method != 'GET':
            return HttpResponseNotAllowed(['GET'])

        try:
            payload = decode(token)
            token = RequestToken.objects.get(id=payload['jti'])
            token.validate_max_uses()
            token.authenticate(request)
            request.token = token

        except (RequestToken.DoesNotExist, InvalidTokenError) as ex:
            key = request.session.session_key
            logger.warning(
                "JWT token error (error code:'%s'): %s", key, ex
            )
            if FOUR03_TEMPLATE:
                response = HttpResponseForbidden(
                    loader.render_to_string(FOUR03_TEMPLATE, context = {'token_error':'Temporary link token error: %s'%key})
                )
            else:
                response = HttpResponseForbidden(
                    u"Temporary link token error (code: %s)" % key
                )
            response.error = ex
            return response
