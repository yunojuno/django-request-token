from __future__ import annotations

import datetime
import logging
from typing import Any

from django.conf import settings
from django.contrib.auth import login
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.http import HttpRequest
from django.utils.timezone import now as tz_now
from django.utils.translation import gettext_lazy as _lazy
from jwt.exceptions import InvalidAudienceError

from .compat import JSONField
from .exceptions import MaxUseError
from .settings import DEFAULT_MAX_USES, JWT_SESSION_TOKEN_EXPIRY
from .utils import encode, to_seconds

logger = logging.getLogger(__name__)


class RequestTokenQuerySet(models.query.QuerySet):
    """Custom QuerySet for RquestToken objects."""

    def create_token(self, scope: str, **kwargs: Any) -> RequestToken:
        """Create a new RequestToken."""
        return RequestToken(scope=scope, **kwargs).save()


class RequestToken(models.Model):
    """
    A link token, targeted for use by a known Django User.

    A RequestToken contains information that can be encoded as a JWT
    (JSON Web Token). It is designed to be used in conjunction with the
    RequestTokenMiddleware (responsible for JWT verification) and the
    @use_request_token decorator (responsible for validating the token
    and setting the request.user correctly).

    Each token must have a 'scope', which is used to tie it to a view function
    that is decorated with the `use_request_token` decorator. The token can
    only be used by functions with matching scopes.

    The token may be set to a specific User, in which case, if the existing
    request is unauthenticated, it will use that user as the `request.user`
    property, allowing access to authenticated views.

    The token may be timebound by the `not_before_time` and `expiration_time`
    properties, which are registered JWT 'claims'.

    The token may be restricted by the number of times it can be used, through
    the `max_use` property, which is incremented each time it's used (NB *not*
    thread-safe).

    The token may also store arbitrary serializable data, which can be used
    by the view function if the request token is valid.

    JWT spec: https://tools.ietf.org/html/rfc7519

    """

    # do not login the user on the request
    LOGIN_MODE_NONE = "None"
    # login the user, but only for the original request
    LOGIN_MODE_REQUEST = "Request"
    # login the user fully, but only for single-use short-duration links
    LOGIN_MODE_SESSION = "Session"

    LOGIN_MODE_CHOICES = (
        (LOGIN_MODE_NONE, _lazy("Do not authenticate")),
        (LOGIN_MODE_REQUEST, _lazy("Authenticate a single request")),
        (LOGIN_MODE_SESSION, _lazy("Authenticate for the entire session")),
    )
    login_mode = models.CharField(
        max_length=10,
        default=LOGIN_MODE_NONE,
        choices=LOGIN_MODE_CHOICES,
        help_text=_lazy("How should the request be authenticated?"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="request_tokens",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        help_text=_lazy(
            "Intended recipient of the JWT (can be used by anyone if not set)."
        ),
    )
    scope = models.CharField(
        max_length=100,
        help_text=_lazy("Label used to match request to view function in decorator."),
    )
    expiration_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_lazy(
            "Token will expire at this time (raises ExpiredSignatureError)."
        ),
    )
    not_before_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_lazy(
            "Token cannot be used before this time (raises ImmatureSignatureError)."
        ),
    )
    data = JSONField(
        help_text=_lazy(
            "Custom data add to the token, but not encoded (must be fetched from DB)."
        ),
        blank=True,
        null=True,
        default=dict,
    )
    issued_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_lazy("Time the token was created (set in the initial save)."),
    )
    max_uses = models.IntegerField(
        default=DEFAULT_MAX_USES,
        help_text=_lazy("The maximum number of times the token can be used."),
    )
    used_to_date = models.IntegerField(
        default=0,
        help_text=_lazy(
            "Number of times the token has been used to date (raises MaxUseError)."
        ),
    )

    objects = RequestTokenQuerySet.as_manager()

    class Meta:
        verbose_name = "Token"
        verbose_name_plural = "Tokens"

    def __str__(self) -> str:
        return "Request token #%s" % (self.id)

    def __repr__(self) -> str:
        return "<RequestToken id={} scope={} login_mode='{}'>".format(
            self.id,
            self.scope,
            self.login_mode,
        )

    @property
    def aud(self) -> int | None:
        """Return 'aud' claim, mapped to user.id."""
        return self.claims.get("aud")

    @property
    def exp(self) -> datetime.datetime | None:
        """Return 'exp' claim, mapped to expiration_time."""
        return self.claims.get("exp")

    @property
    def nbf(self) -> datetime.datetime | None:
        """Return the 'nbf' claim, mapped to not_before_time."""
        return self.claims.get("nbf")

    @property
    def iat(self) -> datetime.datetime | None:
        """Return the 'iat' claim, mapped to issued_at."""
        return self.claims.get("iat")

    @property
    def jti(self) -> int | None:
        """Return the 'jti' claim, mapped to id."""
        return self.claims.get("jti")

    @property
    def max(self) -> int:
        """Return the 'max' claim, mapped to max_uses."""
        return self.claims["max"]

    @property
    def sub(self) -> str:
        """Return the 'sub' claim, mapped to scope."""
        return self.claims["sub"]

    @property
    def claims(self) -> dict:
        """Return dict containing all of the DEFAULT_CLAIMS (where values exist)."""
        claims = {
            "max": self.max_uses,
            "sub": self.scope,
            "mod": self.login_mode[:1].lower(),
        }
        if self.id is not None:
            claims["jti"] = self.id
        if self.user is not None:
            claims["aud"] = str(self.user.pk)
        if self.expiration_time is not None:
            claims["exp"] = to_seconds(self.expiration_time)
        if self.issued_at is not None:
            claims["iat"] = to_seconds(self.issued_at)
        if self.not_before_time is not None:
            claims["nbf"] = to_seconds(self.not_before_time)
        return claims

    def clean(self) -> None:
        """Ensure that login_mode setting is valid."""
        if self.login_mode == RequestToken.LOGIN_MODE_NONE:
            pass
        if self.login_mode == RequestToken.LOGIN_MODE_SESSION:
            if self.user is None:
                raise ValidationError({"user": "Session token must have a user."})

            if self.expiration_time is None:
                raise ValidationError(
                    {"expiration_time": "Session token must have an expiration_time."}
                )
        if self.login_mode == RequestToken.LOGIN_MODE_REQUEST:
            if self.user is None:
                raise ValidationError(
                    {"expiration_time": "Request token must have a user."}
                )

    def save(self, *args: Any, **kwargs: Any) -> RequestToken:
        if "update_fields" not in kwargs:
            self.issued_at = self.issued_at or tz_now()
            if self.login_mode == RequestToken.LOGIN_MODE_SESSION:
                self.expiration_time = self.expiration_time or (
                    self.issued_at
                    + datetime.timedelta(minutes=JWT_SESSION_TOKEN_EXPIRY)
                )
        self.clean()
        super(RequestToken, self).save(*args, **kwargs)
        return self

    def jwt(self) -> str:
        """Encode the token claims into a JWT."""
        return encode(self.claims)

    @transaction.atomic
    def increment_used_count(self) -> None:
        """Add 1 (One) to the used_to_date field."""
        self.used_to_date = models.F("used_to_date") + 1
        self.save()
        # refresh to clear out the F expression, otherwise we risk
        # continuing to update the field.
        # https://docs.djangoproject.com/en/3.2/ref/models/expressions/
        self.refresh_from_db()

    def validate_max_uses(self) -> None:
        """
        Check the token max_uses is still valid.

        Raises MaxUseError if invalid.

        """
        if self.used_to_date >= self.max_uses:
            raise MaxUseError("RequestToken [%s] has exceeded max uses" % self.id)

    def _auth_is_anonymous(self, request: HttpRequest) -> HttpRequest:
        """Authenticate anonymous requests."""
        if request.user.is_authenticated:
            raise InvalidAudienceError("Token requires anonymous user.")

        if self.login_mode == RequestToken.LOGIN_MODE_NONE:
            pass

        if self.login_mode == RequestToken.LOGIN_MODE_REQUEST:
            logger.debug(
                "Setting request.user to %r from token %i.", self.user, self.id
            )
            request.user = self.user

        if self.login_mode == RequestToken.LOGIN_MODE_SESSION:
            logger.debug(
                "Authenticating request.user as %r from token %i.", self.user, self.id
            )
            # I _think_ we can get away with this as we are pulling the
            # user out of the DB, and we are explicitly authenticating
            # the user.
            self.user.backend = "django.contrib.auth.backends.ModelBackend"
            login(request, self.user)

        return request

    def _auth_is_authenticated(self, request: HttpRequest) -> HttpRequest:
        """Authenticate requests with existing users."""
        if request.user.is_anonymous:
            raise InvalidAudienceError("Token requires authenticated user.")

        if self.login_mode == RequestToken.LOGIN_MODE_NONE:
            return request

        if request.user == self.user:
            return request

        raise InvalidAudienceError(
            "RequestToken [%i] audience mismatch: '%s' != '%s'"
            % (self.id, request.user, self.user)
        )

    def authenticate(self, request: HttpRequest) -> HttpRequest:
        """
        Authenticate an HttpRequest with the token user.

        This method encapsulates the request handling - if the token
        has a user assigned, then this will be added to the request.

        """
        if request.user.is_anonymous:
            return self._auth_is_anonymous(request)
        else:
            return self._auth_is_authenticated(request)

    def expire(self) -> None:
        """Mark the token as expired immediately, effectively killing the token."""
        self.expiration_time = tz_now() - datetime.timedelta(microseconds=1)
        self.save()


class RequestTokenLog(models.Model):
    """Used to log the use of a RequestToken."""

    token = models.ForeignKey(
        RequestToken,
        related_name="logs",
        help_text="The RequestToken that was used.",
        on_delete=models.CASCADE,
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        help_text="The user who made the request (None if anonymous).",
    )
    user_agent = models.TextField(
        blank=True, help_text="User-agent of client used to make the request."
    )
    client_ip = models.GenericIPAddressField(
        blank=True,
        null=True,
        unpack_ipv4=True,
        help_text="Client IP of device used to make the request.",
    )
    status_code = models.IntegerField(
        blank=True,
        null=True,
        help_text="Response status code associated with this use of the token.",
    )
    timestamp = models.DateTimeField(
        blank=True, help_text="Time the request was logged."
    )

    class Meta:
        verbose_name = "Log"
        verbose_name_plural = "Logs"

    def __str__(self) -> str:
        if self.user is None:
            return "{} used {}".format(self.token, self.timestamp)
        else:
            return "{} used by {} at {}".format(self.token, self.user, self.timestamp)

    def __repr__(self) -> str:
        return "<RequestTokenLog id={} token={} timestamp='{}'>".format(
            self.id,
            self.token.id,
            self.timestamp,
        )

    def save(self, *args: Any, **kwargs: Any) -> RequestToken:
        if "update_fields" not in kwargs:
            self.timestamp = self.timestamp or tz_now()
        super(RequestTokenLog, self).save(*args, **kwargs)
        return self
