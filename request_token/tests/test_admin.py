# -*- coding: utf-8 -*-
import datetime
import mock

from jwt.exceptions import MissingRequiredClaimError

from django.test import TestCase
from django.utils.timezone import now as tz_now

from ..admin import (
    pretty_print,
    RequestTokenAdmin,
)
from ..models import (
    RequestToken,
)


class AdminTests(TestCase):

    """Admin function tests."""

    def test_pretty_print(self):
        self.assertEqual(pretty_print(None), None)
        self.assertEqual(
            pretty_print({'foo': True}),
            '<code>{\n&nbsp;&nbsp;&nbsp;&nbsp;"foo":&nbsp;true\n}</code>'
        )


class RequestTokenAdminTests(TestCase):

    """RequestTokenAdmin class tests."""

    @mock.patch('request_token.models.tz_now')
    def test_is_valid(self, mock_now):
        now = tz_now()
        mock_now.return_value = now
        token = RequestToken()
        admin = RequestTokenAdmin(RequestToken, None)

        token.not_before_time = now + datetime.timedelta(minutes=1)
        self.assertTrue(token.not_before_time > now)
        self.assertFalse(admin.is_valid(token))

        token.not_before_time = None
        token.expiration_time = now - datetime.timedelta(minutes=1)
        self.assertTrue(token.expiration_time < now)
        self.assertFalse(admin.is_valid(token))

        token.expiration_time = None
        token.max_uses = 1
        token.used_to_date = 1
        self.assertFalse(admin.is_valid(token))

        # finally make it valid
        token.max_uses = 10
        self.assertTrue(admin.is_valid(token))

    def test_jwt(self):
        token = RequestToken(id=1, scope='foo').save()
        admin = RequestTokenAdmin(RequestToken, None)
        self.assertEqual(admin.jwt(token), token.jwt())

        token = RequestToken()
        self.assertRaises(MissingRequiredClaimError, token.jwt)
        self.assertEqual(admin.jwt(token), None)

    def test_pretty_payload(self):
        token = RequestToken(id=1, scope='foo').save()
        admin = RequestTokenAdmin(RequestToken, None)
        self.assertEqual(admin.pretty_payload(token), pretty_print(token.claims))
