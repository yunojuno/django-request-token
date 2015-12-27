# -*- coding: utf-8 -*-
"""django_jwt decorators."""
from functools import wraps
import logging

from jwt import decode

from django_jwt import settings

logger = logging.getLogger(__name__)


def verify_token(func):
    """Decorator used to exapand and verify JWT tokens.
    
    The ``verify_token`` function decorator is responsible for expanding the token according to the following rules:

    1. Extract the token from the querystring if it exists
    2. Verify the token matches the signature
    3. Validate the token ``target_url`` matches the current ``request.path``
    4. If the request is already authenticated, check that the request user and the token user match
    5. If the token has a ``max_uses`` attribute, check that it hasn't been used too many times already
    6. If all the above pass, then set the request.user to the token.user

    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            jwt = request.GET.get(settings.JWT_QUERYSTRING_ARG, None)
            if jwt is None:
                return view_func(request, *args, **kwargs)    
            # now we have a JWT, we can verify it
            headers, payload, signature = decode(token, secret=settings.SECRET_KEY)
            try:
                token = RequestToken.objects.get(id=payload['jti'])
                token.validate(request)
            except RequestToken.DoesNotExist:
                logger.warning("JWT token not found: %s", jwt)
                return HttpResponse("JWT token not found.", status=403)
            except InvalidTokenError as ex:
                return HttpResponse(ex, status=403)
            # # check that target_url matches the current request
            # if token.target_url is not None and token.target_url != request.path:
            #     return HttpResponse("JWT url mismatch", status=403)
            # if token.audience is not None:
            #     # check that request user (if authenticated) matches
            #     if request.user.is_authenticated:
            #         if request.user.username != token.audience:
            #             return HttpResponse("JWT audience mismatch", status=403)
            # request.user = token.user
            # request.jwt = token
            reponse = view_func(request, *args, **kwargs)
            RequestToken.log(request, response)
            return response
        return _wrapped_view
    return decorator(func)