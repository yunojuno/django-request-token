# -*- coding: utf-8 -*-
"""request_token admin models."""
import datetime
import json

from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.timezone import now as tz_now

from request_token.models import RequestToken


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
    readonly_fields = ('pretty_payload', 'jwt', 'issued_at')
    search_fields = ('user__first_name', 'user__username')
    raw_id_fields = ('user',)

    def pretty_payload(self, obj):
        return pretty_print(obj.claims)
    pretty_payload.short_description = "Payload"

    def jwt(self, obj):
        try:
            return obj.jwt()
        except:
            return None
    jwt.short_description = "JWT"

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
