from __future__ import annotations

import json

from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.timezone import now as tz_now

from .models import RequestToken, RequestTokenLog


def pretty_print(data: dict | None) -> str | None:
    """Convert dict into formatted HTML."""
    if data is None:
        return None
    pretty = json.dumps(data, sort_keys=True, indent=4, separators=(",", ": "))
    html = pretty.replace(" ", "&nbsp;").replace("\n", "<br>")
    return mark_safe("<pre><code>%s</code></pre>" % html)  # noqa: S703,S308


class RequestTokenAdmin(admin.ModelAdmin):
    """Admin model for RequestToken objects."""

    list_display = (
        "user",
        "scope",
        "not_before_time",
        "expiration_time",
        "max_uses",
        "used_to_date",
        "issued_at",
        "is_valid",
    )
    readonly_fields = (
        "issued_at",
        "token",
        "_parsed",
        "_claims",
        "_data",
    )
    search_fields = (
        "user__first_name",
        "user__last_name",
        "user__email",
        "user__username",
        "scope",
        "token"
    )
    raw_id_fields = ("user",)

    @admin.display(description="JWT (decoded)")
    def _claims(self, obj: RequestToken) -> str | None:
        return pretty_print(obj.claims)

    @admin.display(description="Data (JSON)")
    def _data(self, obj: RequestToken) -> str | None:
        return pretty_print(obj.data)

    @admin.display(description="JWT (parsed)")
    def _parsed(self, obj: RequestToken) -> str | None:
        try:
            jwt = obj.token.split(".")
            return pretty_print(
                {"header": jwt[0], "claims": jwt[1], "signature": jwt[2]}
            )
        except Exception:  # noqa: B902
            return None

    @admin.display(boolean=True)
    def is_valid(self, obj: RequestToken) -> bool:
        """Validate the time window and usage."""
        now = tz_now()
        if obj.not_before_time and obj.not_before_time > now:
            return False
        if obj.expiration_time and obj.expiration_time < now:
            return False
        if obj.used_to_date >= obj.max_uses:
            return False
        return True


class RequestTokenLogAdmin(admin.ModelAdmin):
    """Admin model for RequestTokenLog objects."""

    list_display = ("token", "user", "status_code", "timestamp")
    search_fields = ("user__first_name", "user__username")
    raw_id_fields = ("user", "token")
    list_filter = ("status_code",)


class RequestTokenErrorLogAdmin(admin.ModelAdmin):
    """Admin model for RequestTokenErrorLog objects."""

    list_display = ("token", "log", "error_type", "error_message")
    search_fields = (
        "log__user__first_name",
        "log__user__last_name",
        "log__user__username",
    )
    raw_id_fields = ("token", "log")
    list_filter = ("error_type",)


admin.site.register(RequestToken, RequestTokenAdmin)
admin.site.register(RequestTokenLog, RequestTokenLogAdmin)
