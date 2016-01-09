# -*- coding: utf-8 -*-
"""request_token.utils tests."""
import datetime

from jwt import decode as jwt_decode, encode as jwt_encode
from jwt.exceptions import MissingRequiredClaimError, DecodeError

from django.conf import settings
from django.test import TestCase

from request_token.utils import encode, decode, to_seconds, MANDATORY_CLAIMS


class FunctionTests(TestCase):

    """Tests for free-floating functions."""

    def test_to_seconds(self):
        timestamp = datetime.datetime(2015, 1, 1)
        self.assertEqual(to_seconds(timestamp), 1420070400)
        self.assertEqual(to_seconds(1420070400), None)

    def test_encode(self):
        payload = {'foo': 'bar'}
        self.assertRaises(MissingRequiredClaimError, encode, payload)
        # force all mandatory claims into the payload
        payload = {k: 'foo' for k in MANDATORY_CLAIMS}
        self.assertEqual(encode(payload), jwt_encode(payload, settings.SECRET_KEY))

    def test_decode(self):
        # check that we can't decode with the wrong secret
        payload = {'foo': 'bar'}
        encoded = jwt_encode(payload, "QWERTYUIO")
        self.assertRaises(DecodeError, decode, encoded)
        # we can decode this, but we're missing the mandatory fields
        encoded = jwt_encode(payload, settings.SECRET_KEY)
        self.assertRaises(MissingRequiredClaimError, decode, encoded)
        # force all mandatory claims into the payload
        payload = {k: 'foo' for k in MANDATORY_CLAIMS}
        encoded = jwt_encode(payload, settings.SECRET_KEY)
        self.assertEqual(decode(encoded), payload)
        self.assertEqual(decode(encoded), jwt_decode(encoded, settings.SECRET_KEY))
