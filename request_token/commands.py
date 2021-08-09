from __future__ import annotations

from django.db import transaction
from django.http import HttpRequest

from request_token.models import RequestToken, RequestTokenLog
from request_token.settings import DISABLE_LOGS


def parse_xff(header_value: str) -> str | None:
    """
    Parse out the X-Forwarded-For request header.

    This handles the bug that blows up when multiple IP addresses are
    specified in the header. The docs state that the header contains
    "The originating IP address", but in reality it contains a list
    of all the intermediate addresses. The first item is the original
    client, and then any intermediate proxy IPs. We want the original.

    Returns the first IP in the list, else None.

    """
    try:
        return header_value.split(",")[0].strip()
    except (KeyError, AttributeError):
        return None


def request_meta(request: HttpRequest) -> dict:
    """Extract values from request to be added to log object."""
    user = None if request.user.is_anonymous else request.user
    xff = parse_xff(request.META.get("HTTP_X_FORWARDED_FOR"))
    remote_addr = request.META.get("REMOTE_ADDR", None)
    user_agent = request.META.get("HTTP_USER_AGENT", "unknown")
    return {"user": user, "client_ip": xff or remote_addr, "user_agent": user_agent}


@transaction.atomic
def log_token_use(
    token: RequestToken, request: HttpRequest, status_code: int
) -> RequestTokenLog | None:
    token.increment_used_count()

    if DISABLE_LOGS:
        return None

    return RequestTokenLog.objects.create(
        token=token, status_code=status_code, **request_meta(request)
    )
