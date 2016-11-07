# -*- coding: utf-8 -*-
import json

from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.timezone import now as tz_now

from .models import (
    RequestToken,
    RequestTokenLog
)


def pretty_print(data):
    """Convert dict into formatted HTML."""
    if data is None:
        return None
    pretty = json.dumps(
        data,
        sort_keys=True,
        indent=4,
        separators=(',', ': ')
    )
    return mark_safe("<code>%s</code>" % pretty.replace(" ", "&nbsp;"))


class RequestTokenAdmin(admin.ModelAdmin):

    """Admin model for RequestToken objects."""

    list_display = (
        'user',
        'scope',
        'not_before_time',
        'expiration_time',
        'max_uses',
        'used_to_date',
        'issued_at',
        'is_valid'
    )
    readonly_fields = ('issued_at', 'jwt', '_parsed', '_claims', '_json')
    search_fields = ('user__first_name', 'user__username')
    raw_id_fields = ('user',)

    def _claims(self, obj):
        return pretty_print(obj.claims)

    _claims.short_description = "JWT (decoded)"

    def _json(self, obj):
        return pretty_print(obj.json)

    _json.short_description = "Data (JSON)"

    def jwt(self, obj):
        try:
            return obj.jwt()
        except:
            return None

    jwt.short_description = "JWT"

    def _parsed(self, obj):
        try:
            jwt = obj.jwt().split('.')
            return pretty_print({
                "header": jwt[0],
                "claims": jwt[1],
                "signature": jwt[2]
            })
        except:
            return None

    _parsed.short_description = "JWT (parsed)"

    def is_valid(self, obj):
        """Validate the time window and usage."""
        now = tz_now()
        if obj.not_before_time and obj.not_before_time > now:
            return False
        if obj.expiration_time and obj.expiration_time < now:
            return False
        if obj.used_to_date >= obj.max_uses:
            return False
        return True

    is_valid.boolean = True


admin.site.register(RequestToken, RequestTokenAdmin)


class RequestTokenLogAdmin(admin.ModelAdmin):

    """Admin model for RequestTokenLog objects."""

    list_display = (
        'token',
        'user',
        'status_code',
        'timestamp'
    )
    search_fields = ('user__first_name', 'user__username')
    raw_id_fields = ('user', 'token')


admin.site.register(RequestTokenLog, RequestTokenLogAdmin)
