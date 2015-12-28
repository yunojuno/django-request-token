# -*- coding: utf-8 -*-
"""django_jwt models."""
import calendar
import datetime
import json

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.db import models, transaction
from django.utils.timezone import now as tz_now

import jwt
from jwt.exceptions import (
    InvalidAudienceError,
    # DecodeError,
    ExpiredSignatureError,
    ImmatureSignatureError,
    # InvalidTokenError,
    MissingRequiredClaimError
)

from django_jwt.exceptions import MaxUseError, TargetUrlError

# list of the formal, 'registered' claims
REGISTERED_CLAIMS = ('iss', 'aud', 'exp', 'nbf', 'iat', 'jti')

# the default decoding is to verify the signature only
DEFAULT_DECODE_OPTIONS = {
    'verify_signature': True,
    'verify_exp': False,
    'verify_nbf': False,
    'verify_iat': False,
    'verify_aud': False,
    'verify_iss': False,
    'require_exp': False,
    'require_iat': False,
    'require_nbf': False
}


def to_seconds(timestamp):
    """Convert timestamp into integers since epoch."""
    try:
        return calendar.timegm(timestamp.utctimetuple())
    except:
        return None


def decode(encoded, options=DEFAULT_DECODE_OPTIONS):
    """Decode JWT and verify the signature.

    Returns the decoded payload.

    """
    return jwt.decode(encoded, settings.SECRET_KEY, options=DEFAULT_DECODE_OPTIONS)


def extract_claim(encoded, claim):
    """Decode and verify JWT, and extract a single claim.

    This function will decode the JWT, verifying the signature only.

    Returns the value of the claim, raises MissingRequiredClaimError if
    the claim does not exist.

    """
    decoded = decode(encoded)
    try:
        return decoded[claim]
    except KeyError:
        raise MissingRequiredClaimError(claim)


class RequestTokenQuerySet(models.query.QuerySet):

    """Custom QuerySet for RquestToken objects."""

    def get_from_jwt(self, encoded):
        """Decode and verify a JWT into a RequestToken.

        This method decodes the JWT, verifies it, and extracts the
        'jti' claim, from which it fetches the relevant RequestToken
        object. Raises DoesNotExist error if it can't be found.

        NB It only verifies the signature - it does *not* verify the
        exp and nbf claims as we want to return the RequestToken before
        validating the token - so we only care that it is untampered,
        and that it has a 'jti' value.

        Args:
            encoded: string, the 3-part 'headers.payload.signature' encoded JWT.

        Returns the matching RequestToken object.

        """
        return self.get(id=extract_claim(encoded, 'jti'))

    def create_token(self, target_url, **kwargs):
        """Create a new RequestToken, setting the target_url."""
        return RequestToken(target_url=target_url, **kwargs).save()


class RequestToken(models.Model):

    """A JWT token, targeted for use by a known Django User.

    > JSON Web Token (JWT) is a compact, URL-safe means of representing
    > claims to be transferred between two parties.

    JWTs are general purpose, however this app (and by extension this model)
    is for a specific use-case - sending out time-bound links to known users
    who are registered (or at least modelled) within a Django project.
    To this end, various of the pre-defined 'registered' claims are
    preset - the issuer (iss) is set to this project, with its value taken
    from the Sites app, and the audience (aud) is set to a single User object.

    The time-bound claims (expiration time (exp) and 'not before' (nbf)) are set on a
    per-token basis. In addition, we have a max uses (max) claim that can
    be used to restric usage of the token (e.g. one-time use).

    JWT spec: https://tools.ietf.org/html/rfc7519

    """
    user = models.ForeignKey(
        User,
        blank=True, null=True,
        help_text="Intended recipient of the JWT."
    )
    target_url = models.CharField(
        max_length=200,
        help_text="The target endpoint."
    )
    expiration_time = models.DateTimeField(
        blank=True, null=True,
        help_text="Token will expire at this time (raises ExpiredSignatureError)."
    )
    not_before_time = models.DateTimeField(
        blank=True, null=True,
        help_text="Token cannot be used before this time (raises ImmatureSignatureError)."
    )
    data = models.TextField(
        max_length=1000,
        help_text="Custom data (JSON) added to the default payload.",
        blank=True,
        default='{}'
    )
    issued_at = models.DateTimeField(
        blank=True, null=True,
        help_text="Time the token was created (set in the initial save)."
    )
    max_uses = models.IntegerField(
        default=1,
        help_text="The maximum number of times the token can be used."
    )
    used_to_date = models.IntegerField(
        default=0,
        help_text="Number times the token has been used to date (raises MaxUseError)."
    )

    objects = RequestTokenQuerySet.as_manager()

    def save(self, *args, **kwargs):
        if 'update_fields' not in kwargs:
            self.issued_at = self.issued_at or tz_now()
        super(RequestToken, self).save(*args, **kwargs)
        return self

    @property
    def iss(self):
        """Issuer claim."""
        return Site.objects.get_current().domain

    @property
    def aud(self):
        """Audience claim."""
        if self.user is None:
            return None
        else:
            return self.user.username

    @property
    def exp(self):
        """Expiration time claim."""
        return to_seconds(self.expiration_time)

    @property
    def nbf(self):
        """Not before time claim."""
        return to_seconds(self.not_before_time)

    @property
    def iat(self):
        """Issued at claim."""
        return to_seconds(self.issued_at)

    @property
    def jti(self):
        """JWT id claim."""
        return self.id

    @property
    def registered_claims(self):
        """Return the registered claims portion of the token."""
        claims = {}
        for claim in REGISTERED_CLAIMS:
            claim_value = getattr(self, claim, None)
            if claim_value is not None:
                claims[claim] = claim_value
        return claims

    @property
    def payload(self):
        """The payload to be encoded."""
        claims = self.registered_claims
        claims.update(json.loads(self.data))
        return claims

    def encode(self):
        """Encode the JWT.

        This is where the token is built up and then
        encoded. It uses the `payload` property as the
        token payload, which includes within it all of
        the supplied registered claims, combined with the
        `data` values.

        It is signed using the Django SECRET_KEY value.

        """
        assert self.id is not None, (
            "RequestToken missing `id` - ensure that "
            "the token is saved before calling the `encode` method."
        )
        return jwt.encode(self.payload, settings.SECRET_KEY)

    def validate(self):
        """Validate token expiry and max uses."""
        self._validate_expiry()
        self._validate_max_uses()

    def _validate_expiry(self):
        """Validate the not before and expiry dates.

        Raises jwt ImmatureSignatureError or ExpiredSignatureError.

        """
        now = tz_now()
        if now < (self.not_before_time or datetime.datetime.min):
            raise ImmatureSignatureError()
        if now > (self.expiration_time or datetime.datetime.max):
            raise ExpiredSignatureError()

    def _validate_max_uses(self):
        """Check that we haven't exceeded the max_uses value.

        Raise MaxUseError if we have overshot the value.

        """
        if self.used_to_date >= self.max_uses:
            raise MaxUseError("JWT has exceeded max uses")

    def validate_request(self, request):
        """Validate a request against the token object.

        Sets the request.user object to the token.recipient _if_ all
        validation passes, else raises InvalidTokenError.

        NB This does **not** verify the JWT signature - this must be done
        elsewhere.

        Args:
            request: HttpRequest object to validate.

        """
        self._validate_request_url(request)
        self._validate_request_user(request)
        request.token = self

    def _validate_request_url(self, request):
        """Confirm that request.path and target_url match.

        Raises TargetUrlError if they don't match.

        """
        # check that target_url matches the current request
        if self.target_url in ('', None):
            return
        if self.target_url != request.path:
            raise TargetUrlError("JWT url mismatch")

    def _validate_request_user(self, request):
        """Validate and set the request.user from object user.

        If the object has a user set, then it must match the request.user,
        and if it doesn't we raise an InvalidAudienceError.

        """
        assert hasattr(request, 'user'), (
            "Request is missing user property. Please ensure that the Django "
            "authentication middleware is installed."
        )

        if self.user is None:
            return

        # we have a token user set, and an anonymous user on the request,
        # so replace that with the token user
        if request.user.is_anonymous():
            request.user = self.user
            return

        # we have an authenticated user that does *not* match the user
        # we are expecting, so bomb out here.
        if request.user != self.user:
            raise InvalidAudienceError("JWT audience mismatch")

    @transaction.atomic
    def log(self, request, response):
        """Record the use of a token.

        This is used by the decorator to log each time someone uses the token,
        or tries to. Used for reporting, diagnostics.

        Args:
            request: the HttpRequest object that used the token, from which the
                user, ip and user-agenct are extracted.
            response: the corresponding HttpResponse object, from which the status
                code is extracted.
            duration: float, the duration of the view function in ms - just because
                you can never measure too many things.

        Returns a RequestTokenUse object.

        """
        assert hasattr(request, 'user'), (
            "Request is missing user property. Please ensure that the Django "
            "authentication middleware is installed."
        )
        meta = request.META
        xff = meta.get('HTTP_X_FORWARDED_FOR', None)
        client_ip = xff or meta.get('REMOTE_ADDR', 'unknown')
        user = None if request.user.is_anonymous() else request.user
        rtu = RequestTokenLog(
            token=self,
            user=user,
            user_agent=meta.get('HTTP_USER_AGENT', 'unknown'),
            client_ip=client_ip,
            status_code=response.status_code
        ).save()
        # NB this could already be out-of-date
        self.used_to_date = models.F('used_to_date') + 1
        self.save()
        return rtu


class RequestTokenLog(models.Model):

    """Used to log the use of a RequestToken."""

    token = models.ForeignKey(
        RequestToken,
        help_text="The RequestToken that was used.",
        db_index=True
    )
    user = models.ForeignKey(
        User,
        blank=True, null=True,
        help_text="The user who made the request (None if anonymous)."
    )
    user_agent = models.TextField(
        blank=True,
        help_text="User-agent of client used to make the request."
    )
    client_ip = models.CharField(
        max_length=15,
        help_text="Client IP of device used to make the request."
    )
    status_code = models.IntegerField(
        blank=True, null=True,
        help_text="Response status code associated with this use of the token."
    )
    timestamp = models.DateTimeField(
        blank=True,
        help_text="Time the request was logged."
    )

    def save(self, *args, **kwargs):
        if 'update_fields' not in kwargs:
            self.timestamp = self.timestamp or tz_now()
        super(RequestTokenLog, self).save(*args, **kwargs)
        return self
