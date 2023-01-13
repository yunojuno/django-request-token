import datetime

import pytest
from django.conf import settings
from django.test import TestCase
from jwt import encode as jwt_encode
from jwt.exceptions import DecodeError, InvalidAlgorithmError, MissingRequiredClaimError

from request_token.utils import MANDATORY_CLAIMS, decode, encode, is_jwt, to_seconds


class FunctionTests(TestCase):
    """Tests for free-floating functions."""

    def test_to_seconds(self):
        timestamp = datetime.datetime(2015, 1, 1)
        self.assertEqual(to_seconds(timestamp), 1420070400)
        self.assertEqual(to_seconds(1420070400), None)

    def test_encode(self):
        payload = {"foo": "bar"}
        self.assertRaises(MissingRequiredClaimError, encode, payload)
        # force all mandatory claims into the payload
        payload = {k: "foo" for k in MANDATORY_CLAIMS}
        self.assertEqual(encode(payload), jwt_encode(payload, settings.SECRET_KEY))

    def test_decode(self):
        # test valid encode / decode
        payload = {k: "foo" for k in MANDATORY_CLAIMS}
        encoded = jwt_encode(payload, settings.SECRET_KEY)
        self.assertEqual(decode(encoded), payload)

    def test_decode__wrong_secret(self):
        # check that we can't decode with the wrong secret
        payload = {k: "foo" for k in MANDATORY_CLAIMS}
        encoded = jwt_encode(payload, "QWERTYUIO")
        self.assertRaises(DecodeError, decode, encoded)

    def test_decode__missing_claims(self):
        # we can decode this, but we're missing the mandatory fields
        payload = {"foo": "bar"}
        encoded = jwt_encode(payload, settings.SECRET_KEY)
        self.assertRaises(MissingRequiredClaimError, decode, encoded)

    def test_decode__invalid_algo(self):
        # check that we can't decode with the wrong algorithms
        payload = {"foo": "bar"}
        encoded = jwt_encode(payload, settings.SECRET_KEY)
        self.assertRaises(InvalidAlgorithmError, decode, encoded, algorithms=["HS384"])


@pytest.mark.parametrize(
    "jwt,result",
    [
        (None, False),
        ("", False),
        ("123.abc.DEF", False),
    ],
)
def test_is_jwt__False(jwt: str, result: bool) -> None:
    assert is_jwt(jwt) == result


def test_is_jwt__True() -> None:
    encoded = jwt_encode({}, settings.SECRET_KEY)
    assert is_jwt(encoded)
