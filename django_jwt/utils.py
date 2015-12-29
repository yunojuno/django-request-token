# -*- coding: utf-8 -*-
"""Basic encode/decode utils, taken from PyJWT."""
import calendar

from jwt import encode as jwt_encode
from jwt import decode as jwt_decode
from jwt import exceptions

from django.conf import settings

# verification options - signature and expiry date
DEFAULT_DECODE_OPTIONS = {
    'verify_signature': True,
    'verify_exp': True,
    'verify_nbf': True,
    'verify_iat': True,
    'verify_aud': False,
    'verify_iss': False,  # we're only validating our own claims
    'require_exp': False,
    'require_iat': False,
    'require_nbf': False
}


def encode(payload):
    """Encode JSON payload (using SECRET_KEY)."""
    return jwt_encode(payload, settings.SECRET_KEY)


def decode(token, options=DEFAULT_DECODE_OPTIONS):
    """Decode JWT payload (using SECRET_KEY)."""
    decoded = jwt_decode(token, settings.SECRET_KEY, options=options)
    if 'jti' not in decoded:
        raise exceptions.MissingRequiredClaimError('jti')
    return decoded


def to_seconds(timestamp):
    """Convert timestamp into integers since epoch."""
    try:
        return calendar.timegm(timestamp.utctimetuple())
    except:
        return None
