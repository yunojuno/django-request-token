from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import SimpleLazyObject


def request_token(request):
    """Adds a request_token to template context (if found on the request)."""
    def _get_val():
        try:
            return request.token.jwt()
        except AttributeError:
            raise ImproperlyConfigured(
                "Request has no 'token' attribute - is RequestTokenMiddleware installed?"
            )

    return {'request_token': SimpleLazyObject(_get_val)}
