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
    audience = models.ForeignKey(
        User,
        blank=True, null=True,
        help_text="Intended recipient of the JWT."
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
        return self.audience.username

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
