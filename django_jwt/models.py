# -*- coding: utf-8 -*-
"""django_jwt models."""
import calendar
import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.db import models
from django.utils.timezone import now as tz_now

import jwt

REGISTERED_CLAIMS = ('iss', 'aud', 'exp', 'nbf', 'iat', 'jti')


def to_seconds(timestamp):
    """Convert timestamp into integers since epoch."""
    try:
        return calendar.timegm(timestamp.utctimetuple())
    except:
        return None


class RequestTokenQuerySet(models.query.QuerySet):

    """Custom QuerySet for RquestToken objects."""

    def decode(self, encoded):
        """Decodes and verifies a JWT into a RequestToken.

        This method decodes the JWT, verifies it, and extracts the
        'jti' claim, from which it fetches the relevant RequestToken
        object. Raises DoesNotExist error if it can't be found.

        Args:
            encoded: string, the 3-part 'headers.payload.signature' encoded JWT.

        Returns the matching RequestToken object.

        """
        headers, payload, signature = jwt.decode(encoded, secret=settings.SECRET_KEY)
        return self.get(id=payload['jti'])


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
    recipient = models.ForeignKey(
        User,
        blank=True, null=True,
        help_text="Intended recipient of the JWT."
    )
    target_url = models.CharField(
        blank=True,
        help_text="The target endpoint."
    )
    expiration_time = models.DateTimeField(
        blank=True, null=True,
        help_text="Time at which this token expires."
    )
    not_before_time = models.DateTimeField(
        blank=True, null=True,
        help_text="Time before which this token is invalid."
    )
    data = models.TextField(
        max_length=1000,
        help_text="Custom data (JSON) added to the default payload.",
        blank=True
    )
    issued_at = models.DateTimeField(
        blank=True, null=True,
        help_text="Time the token was created, set in the initial save."
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
        if self.recipient is None:
            return None
        else:
            return self.recipient.username

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
        claims.update(self.data)
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
        assert self.id is not None, ("RequestToken missing `id` - ensure that "
            "the token is saved before calling the `encode` method.")
        return jwt.encode(self.payload, settings.SECRET_KEY)

    def validate_request(self, request):
        """Validate a request against the token object.

        Sets the request.user object to the token.recipient _if_ all
        validation passes, else raises InvalidTokenError.

        NB This does **not** verify the JWT signature - this must be done
        elsewhere.

        Args:
            request: HttpRequest object to validate.

        """
        # check that target_url matches the current request
        if self.target_url is not None and self.target_url != request.path:
            raise InvalidTokenError("JWT url mismatch")
        if self.audience is not None:
            # check that request user (if authenticated) matches
            if request.user.is_authenticated():
                if request.user.username != self.aud:
                    return InvalidTokenError("JWT audience mismatch")
        if self.used_to_date >= self.max_uses:
            raise InvalidTokenError("JWT has exceeded max uses")
        request.token = self
        request.user = self.recipient

    def log_usage(self, request, response, duration):
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
        meta = request.META
        ff = meta.get('HTTP_X_FORWARDED_FOR', None)
        ra = meta.get('REMOTE_ADDR', 'unknown')
        rtu = RequestTokenUse(
            token=self,
            user=request.user,
            user_agent=meta.get('HTTP_USER_AGENT', 'unknown'),
            source_ip=ff or ra
        )
        rtu.save()
        self.uses += 1
        self.save()
        return rtu
