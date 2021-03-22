from __future__ import annotations

from django.apps import AppConfig


class RequestTokenAppConfig(AppConfig):
    """AppConfig for request_token app."""

    name = "request_token"
    verbose_name = "JWT Request Tokens"
