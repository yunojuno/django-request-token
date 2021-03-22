from __future__ import annotations

import json
from typing import Optional

from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.timezone import now as tz_now

from .models import RequestToken, RequestTokenLog


def pretty_print(data: Optional[dict]) -> Optional[str]:
    """Convert dict into formatted HTML."""
    if data is None:
        return None
    pretty = json.dumps(data, sort_keys=True, indent=4, separators=(",", ": "))
    html = pretty.replace(" ", "&nbsp;").replace("\n", "<br>")
    return mark_safe("<pre><code>%s</code></pre>" % html)


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
    readonly_fields = ("issued_at", "jwt", "_parsed", "_claims", "_data")
    search_fields = (
        "user__first_name",
        "user__last_name",
        "user__email",
        "user__username",
        "scope",
    )
    raw_id_fields = ("user",)

    def _claims(self, obj: RequestToken) -> Optional[str]:
        return pretty_print(obj.claims)

    _claims.short_description = "JWT (decoded)"  # type: ignore

    def _data(self, obj: RequestToken) -> Optional[str]:
        return pretty_print(obj.data)

    _data.short_description = "Data (JSON)"  # type: ignore

    def jwt(self, obj: RequestToken) -> Optional[str]:
        try:
            return obj.jwt()
        except Exception:  # pylint: disable=broad-except
            return None

    jwt.short_description = "JWT"  # type: ignore

    def _parsed(self, obj: RequestToken) -> Optional[str]:
        try:
            jwt = obj.jwt().split(".")
            return pretty_print(
                {"header": jwt[0], "claims": jwt[1], "signature": jwt[2]}
            )
        except Exception:  # pylint: disable=broad-except
            return None

    _parsed.short_description = "JWT (parsed)"  # type: ignore

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

    is_valid.boolean = True  # type: ignore


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
