from __future__ import annotations

import json

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.safestring import mark_safe
from django.utils.timezone import now as tz_now
from jwt.exceptions import DecodeError

from .models import RequestToken, RequestTokenLog
from .utils import decode, is_jwt


def pretty_print(data: dict | None) -> str | None:
    """Convert dict into formatted HTML."""
    if data is None:
        return None
    pretty = json.dumps(data, sort_keys=True, indent=4, separators=(",", ": "))
    html = pretty.replace(" ", "&nbsp;").replace("\n", "<br>")
    return mark_safe("<pre><code>%s</code></pre>" % html)  # noqa: S703,S308


@admin.register(RequestToken)
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

    def get_search_results(
        self, request: HttpRequest, queryset: QuerySet[RequestToken], search_term: str
    ) -> tuple[QuerySet[RequestToken], bool]:
        """Override search to short-circuit if a JWT is identified."""
        if not is_jwt(search_term):
            return super().get_search_results(request, queryset, search_term)
        try:
            pk = decode(search_term)["jti"]
        except DecodeError as ex:
            self.message_user(
                request,
                f"Search term interpreted as JWT - but decoding failed: {ex}",
                "error",
            )
            return super().get_search_results(request, queryset, search_term)
        queryset = RequestToken.objects.filter(pk=pk)
        if queryset.exists():
            self.message_user(
                request,
                "Search term interpreted as JWT - match found.",
                "success",
            )
        else:
            self.message_user(
                request,
                "Search term interpreted as JWT - no match found.",
                "error",
            )
        return queryset, False

    @admin.display(description="JWT (decoded)")
    def _claims(self, obj: RequestToken) -> str | None:
        return pretty_print(obj.claims)

    @admin.display(description="Data (JSON)")
    def _data(self, obj: RequestToken) -> str | None:
        return pretty_print(obj.data)

    @admin.display(description="JWT")
    def jwt(self, obj: RequestToken) -> str | None:
        try:
            return obj.jwt()
        except Exception:  # noqa: B902
            return None

    @admin.display(description="JWT (parsed)")
    def _parsed(self, obj: RequestToken) -> str | None:
        try:
            jwt = obj.jwt().split(".")
            return pretty_print(
                {"header": jwt[0], "claims": jwt[1], "signature": jwt[2]}
            )
        except Exception:  # noqa: B902
            return None

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


@admin.register(RequestTokenLog)
class RequestTokenLogAdmin(admin.ModelAdmin):
    """Admin model for RequestTokenLog objects."""

    list_display = ("token", "user", "status_code", "timestamp")
    search_fields = ("user__first_name", "user__username")
    raw_id_fields = ("user", "token")
    list_filter = ("status_code",)
