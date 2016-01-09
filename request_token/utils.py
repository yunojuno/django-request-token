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

MANDATORY_CLAIMS = ('jti', 'sub', 'mod')


def check_mandatory_claims(payload, claims=MANDATORY_CLAIMS):
    """Check dict for mandatory claims."""
    for claim in claims:
        if claim not in payload:
            raise exceptions.MissingRequiredClaimError(claim)


def encode(payload, check_claims=MANDATORY_CLAIMS):
    """Encode JSON payload (using SECRET_KEY)."""
    check_mandatory_claims(payload, claims=check_claims)
    return jwt_encode(payload, settings.SECRET_KEY)


def decode(token, options=DEFAULT_DECODE_OPTIONS, check_claims=MANDATORY_CLAIMS):
    """Decode JWT payload and check for 'jti', 'sub' claims."""
    decoded = jwt_decode(token, settings.SECRET_KEY, options=options)
    check_mandatory_claims(decoded, claims=check_claims)
    return decoded


def to_seconds(timestamp):
    """Convert timestamp into integers since epoch."""
    try:
        return calendar.timegm(timestamp.utctimetuple())
    except:
        return None
