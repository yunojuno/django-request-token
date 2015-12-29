# -*- coding: utf-8 -*-
"""django_jwt.utils tests."""
import datetime

from jwt import decode as jwt_decode
from jwt.exceptions import MissingRequiredClaimError

from django.conf import settings
from django.test import TestCase

from django_jwt.utils import encode, decode, to_seconds


class FunctionTests(TestCase):

    """Tests for free-floating functions."""

    def test_to_seconds(self):
        timestamp = datetime.datetime(2015, 1, 1)
        self.assertEqual(to_seconds(timestamp), 1420070400)
        self.assertEqual(to_seconds(1420070400), None)

    def test_encode_decode(self):
        encoded = encode({'foo': 'bar'})
        self.assertRaises(MissingRequiredClaimError, decode, encoded)

        encoded = encode({'jti': 123})
        self.assertEqual(decode(encoded), jwt_decode(encoded, settings.SECRET_KEY))
        self.assertEqual(decode(encoded), {'jti': 123})
