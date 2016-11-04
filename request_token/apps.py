# -*- coding: utf-8 -*-
from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured
from django.template import loader, TemplateDoesNotExist

from .settings import FOUR03_TEMPLATE


class RequestTokenAppConfig(AppConfig):

    """AppConfig for request_token app."""

    name = 'request_token'
    verbose_name = "JWT Request Tokens"
    configs = []

    def ready(self):
        """Validate config and connect signals."""
        super(RequestTokenAppConfig, self).ready()
        if FOUR03_TEMPLATE:
            check_template(FOUR03_TEMPLATE)


def check_template(template):
    """Check for the existance of the custom 403 page."""
    try:
        loader.get_template(template)
    except TemplateDoesNotExist:
        raise ImproperlyConfigured(
            "Custom request token template does not exist: '%s'"
            % template
        )
