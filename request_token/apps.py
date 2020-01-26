from __future__ import annotations

from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured
from django.template import TemplateDoesNotExist, loader

from .settings import FOUR03_TEMPLATE


class RequestTokenAppConfig(AppConfig):
    """AppConfig for request_token app."""

    name = "request_token"
    verbose_name = "JWT Request Tokens"

    def ready(self) -> None:
        """Validate config and connect signals."""
        super(RequestTokenAppConfig, self).ready()
        if FOUR03_TEMPLATE:
            check_template(FOUR03_TEMPLATE)


def check_template(template: str) -> None:
    """Check for the existance of the custom 403 page."""
    try:
        loader.get_template(template)
    except TemplateDoesNotExist:
        raise ImproperlyConfigured(
            f"Custom request token template does not exist: '{template}'"
        )
