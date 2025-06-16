"""Basic encode/decode utils, taken from PyJWT."""

from __future__ import annotations

import calendar
import datetime
from typing import Sequence

from django.conf import settings
from jwt import (
    decode as jwt_decode,
    encode as jwt_encode,
    exceptions,
    get_unverified_header,
)

# verification options - signature and expiry date
DEFAULT_DECODE_OPTIONS = {
    "verify_signature": True,
    "verify_exp": True,
    "verify_nbf": True,
    "verify_iat": True,
    "verify_aud": False,
    "verify_iss": False,  # we're only validating our own claims
    "require_exp": False,
    "require_iat": False,
    "require_nbf": False,
}

MANDATORY_CLAIMS = ("jti", "sub", "mod")


def check_mandatory_claims(
    payload: dict, claims: Sequence[str] = MANDATORY_CLAIMS
) -> None:
    """Check dict for mandatory claims."""
    for claim in claims:
        if claim not in payload:
            raise exceptions.MissingRequiredClaimError(claim)


def encode(payload: dict, check_claims: Sequence[str] = MANDATORY_CLAIMS) -> str:
    """Encode JSON payload (using SECRET_KEY)."""
    check_mandatory_claims(payload, claims=check_claims)
    return jwt_encode(payload, settings.SECRET_KEY)


def decode(
    token: str,
    options: dict[str, bool] | None = None,
    check_claims: Sequence[str] | None = None,
    algorithms: list[str] | None = None,
) -> dict:
    """Decode JWT payload and check for 'jti', 'sub' claims."""
    if not options:
        options = DEFAULT_DECODE_OPTIONS
    if not check_claims:
        check_claims = MANDATORY_CLAIMS
    if not algorithms:
        # default encode algorithm - see PyJWT.encode
        algorithms = ["HS256"]
    decoded = jwt_decode(
        token, settings.SECRET_KEY, algorithms=algorithms, options=options
    )
    check_mandatory_claims(decoded, claims=check_claims)
    return decoded


def to_seconds(timestamp: datetime.datetime) -> int | None:
    """Convert timestamp into integers since epoch."""
    try:
        return calendar.timegm(timestamp.utctimetuple())
    except Exception:  # noqa: BLE001
        return None


def is_jwt(jwt: str) -> bool:
    """Return True if the value supplied is a JWT."""
    if not jwt:
        return False
    try:
        header = get_unverified_header(jwt)
    except exceptions.DecodeError:
        return False
    else:
        return header["typ"].lower() == "jwt"
