# -*- coding: utf-8 -*-
"""django_jwt model tests."""
import datetime
import json

from jwt import encode as jwt_encode, decode as jwt_decode
from jwt.exceptions import (
    InvalidAudienceError,
    MissingRequiredClaimError,
    ImmatureSignatureError,
    ExpiredSignatureError
)

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sites.models import Site
from django.http import HttpResponse
from django.test import TransactionTestCase, RequestFactory
from django.utils.timezone import now as tz_now

from django_jwt.models import (
    RequestToken,
    RequestTokenLog,
    REGISTERED_CLAIMS,
    to_seconds,
    decode,
    extract_claim
)
from django_jwt.exceptions import (
    MaxUseError,
    TargetUrlError
)


class FunctionTests(TransactionTestCase):

    """Tests for free-floating functions."""

    def test_to_seconds(self):
        timestamp = datetime.datetime(2015, 1, 1)
        self.assertEqual(to_seconds(timestamp), 1420070400)
        self.assertEqual(to_seconds(1420070400), None)

    def test_decode(self):
        encoded = jwt_encode({'foo': 'bar'}, settings.SECRET_KEY)
        self.assertEqual(decode(encoded), jwt_decode(encoded, settings.SECRET_KEY))
        self.assertEqual(decode(encoded), {'foo': 'bar'})

    def test_extract_claim(self):
        encoded = jwt_encode({'foo': 'bar'}, settings.SECRET_KEY)
        self.assertEqual(extract_claim(encoded, 'foo'), 'bar')
        self.assertRaises(MissingRequiredClaimError, extract_claim, encoded, 'baz')


class RequestTokenTests(TransactionTestCase):

    """RequestToken model property and method tests."""

    def setUp(self):
        self.user = get_user_model().objects.create_user('zoidberg')

    def test_defaults(self):
        token = RequestToken()
        self.assertIsNone(token.user)
        self.assertEqual(token.target_url, '')
        self.assertIsNone(token.expiration_time)
        self.assertIsNone(token.not_before_time)
        self.assertEqual(token.data, "{}")
        self.assertIsNone(token.issued_at)
        self.assertEqual(token.max_uses, 1)
        self.assertEqual(token.used_to_date, 0)

    def test_save(self):
        token = RequestToken().save()
        self.assertIsNotNone(token)
        self.assertIsNone(token.user)
        self.assertEqual(token.target_url, '')
        self.assertIsNone(token.expiration_time)
        self.assertIsNone(token.not_before_time)
        self.assertEqual(token.data, "{}")
        self.assertIsNotNone(token.issued_at)
        self.assertEqual(token.max_uses, 1)
        self.assertEqual(token.used_to_date, 0)

    def test_registered_claims(self):
        self.assertTrue('iss' in REGISTERED_CLAIMS)
        self.assertTrue('aud' in REGISTERED_CLAIMS)
        self.assertTrue('exp' in REGISTERED_CLAIMS)
        self.assertTrue('nbf' in REGISTERED_CLAIMS)
        self.assertTrue('iat' in REGISTERED_CLAIMS)
        self.assertTrue('jti' in REGISTERED_CLAIMS)

        token = RequestToken()
        site = Site.objects.get_current()
        self.assertEqual(getattr(token, 'iss'), site.domain)
        self.assertIsNone(getattr(token, 'aud'))
        self.assertIsNone(getattr(token, 'exp'))
        self.assertIsNone(getattr(token, 'nbf'))
        self.assertIsNone(getattr(token, 'iat'))
        self.assertIsNone(getattr(token, 'jti'))
        claims = {'iss': site.domain}
        self.assertEqual(token.registered_claims, claims)

        # now let's set some properties
        token.user = self.user
        claims['aud'] = self.user.username
        self.assertEqual(token.aud, self.user.username)
        self.assertEqual(token.registered_claims, claims)

        now = tz_now()
        now_sec = to_seconds(now)

        token.expiration_time = now
        claims['exp'] = token.exp
        self.assertEqual(token.exp, now_sec)
        self.assertEqual(token.registered_claims, claims)

        token.not_before_time = now
        claims['nbf'] = token.nbf
        self.assertEqual(token.nbf, now_sec)
        self.assertEqual(token.registered_claims, claims)

        # saving updates the id and issued_at timestamp
        token.save()
        claims['jti'] = token.id
        claims['iat'] = token.iat
        self.assertEqual(token.jti, token.id)
        self.assertEqual(token.iat, to_seconds(token.issued_at))
        self.assertEqual(token.registered_claims, claims)

    def test_payload(self):
        token = RequestToken()
        claims = token.registered_claims
        self.assertEqual(token.payload, claims)
        token.data = json.dumps({'foo': 123})
        claims.update({'foo': 123})
        self.assertEqual(token.payload, claims)

    def test_encode(self):
        token = RequestToken()
        self.assertRaises(AssertionError, token.encode)
        token.id = 1

        encoded = token.encode()
        self.assertEqual(encoded, jwt_encode(token.payload, settings.SECRET_KEY))
        self.assertEqual(decode(encoded, settings.SECRET_KEY), token.payload)

    def test__validate_expiry(self):
        token = RequestToken()
        token._validate_expiry()
        token.expiration_time = tz_now() - datetime.timedelta(days=1)
        self.assertRaises(ExpiredSignatureError, token._validate_expiry)
        token.expiration_time = None
        token.not_before_time = tz_now() + datetime.timedelta(days=1)
        self.assertRaises(ImmatureSignatureError, token._validate_expiry)

    def test__validate_max_uses(self):
        token = RequestToken()
        token._validate_max_uses()
        token.used_to_date = token.max_uses
        self.assertRaises(MaxUseError, token._validate_max_uses)
        token.used_to_date = token.max_uses + 1
        self.assertRaises(MaxUseError, token._validate_max_uses)

    def test_validate(self):
        token = RequestToken()
        token.validate()
        token.used_to_date = token.max_uses
        self.assertRaises(MaxUseError, token.validate)
        token.used_to_date = 0
        token.expiration_time = tz_now() - datetime.timedelta(seconds=1)
        self.assertRaises(ExpiredSignatureError, token.validate)
        token.expiration_time = None
        token.not_before_time = tz_now() + datetime.timedelta(days=1)
        self.assertRaises(ImmatureSignatureError, token._validate_expiry)

    def test__validate_request_url(self):
        # target_url is None
        token = RequestToken()
        factory = RequestFactory()
        request = factory.get('/foo')
        token._validate_request_url(request)
        token.target_url = '/bar'
        self.assertRaises(TargetUrlError, token.validate_request, request)

    def test__validate_request_user(self):

        # target_url is None
        token = RequestToken()
        factory = RequestFactory()
        request = factory.get('/foo')

        # request.user must exist
        self.assertRaises(AssertionError, token._validate_request_user, request)
        request.user = None
        token._validate_request_user(request)
        self.assertIsNone(request.user)

        # user is unchanged as we don't specify a token.user
        anon = AnonymousUser()
        request.user = anon
        token._validate_request_user(request)
        self.assertEqual(request.user, anon)

        # now we are specifying a user, and we have an AnonymousUser in the
        # request - this is the core use case - should be replaced by the token user
        token.user = self.user
        token._validate_request_user(request)
        self.assertEqual(request.user, token.user)

        wrong_user = get_user_model().objects.create_user(username="Finbar")
        request.user = wrong_user
        self.assertNotEqual(request.user, token.user)
        self.assertRaises(InvalidAudienceError, token._validate_request_user, request)

    def test_validate_request(self):
        token = RequestToken(user=self.user)
        factory = RequestFactory()
        request = factory.get('/foo')
        request.user = self.user
        token.validate_request(request)
        self.assertEqual(request.token, token)
        self.assertEqual(request.user, token.user)

    def test_log(self):
        token = RequestToken().save()
        factory = RequestFactory()
        request = factory.get('/')
        request.user = AnonymousUser()
        request.META = {}
        response = HttpResponse("foo", status=123)

        def assertUsedToDate(expected):
            token.refresh_from_db(fields=['used_to_date'])
            self.assertEqual(token.used_to_date, expected)

        log = token.log(request, response)
        self.assertEqual(RequestTokenLog.objects.get(), log)
        self.assertEqual(log.user, None)
        self.assertEqual(log.token, token)
        self.assertEqual(log.user_agent, 'unknown')
        self.assertEqual(log.client_ip, 'unknown')
        self.assertEqual(log.status_code, 123)
        assertUsedToDate(1)

        request.META['REMOTE_ADDR'] = '192.168.0.1'
        log = token.log(request, response)
        self.assertEqual(log.client_ip, '192.168.0.1')
        assertUsedToDate(2)

        request.META['HTTP_X_FORWARDED_FOR'] = '192.168.0.2'
        log = token.log(request, response)
        self.assertEqual(log.client_ip, '192.168.0.2')
        assertUsedToDate(3)

        request.META['HTTP_USER_AGENT'] = 'test_agent'
        log = token.log(request, response)
        self.assertEqual(log.user_agent, 'test_agent')
        token.refresh_from_db(fields=['used_to_date'])
        assertUsedToDate(4)


class RequestTokenQuerySetTests(TransactionTestCase):

    """RequestTokenQuerySet class tests."""

    def test_get_from_jwt(self):
        token = RequestToken()
        token.save()
        encoded = token.encode()
        self.assertEqual(RequestToken.objects.get_from_jwt(encoded), token)

    def test_create_token(self):
        self.assertRaises(TypeError, RequestToken.objects.create_token)
        token = RequestToken.objects.create_token(target_url="/")
        self.assertEqual(RequestToken.objects.get().target_url, '/')

class RequestTokenLogTests(TransactionTestCase):

    """RequestTokenLog model property and method tests."""

    def setUp(self):
        self.user = get_user_model().objects.create_user('zoidberg')
        self.token = RequestToken(user=self.user).save()

    def test_defaults(self):
        log = RequestTokenLog(
            token=self.token,
            user=self.user
        )
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.token, self.token)
        self.assertEqual(log.user_agent, '')
        self.assertEqual(log.client_ip, '')
        self.assertIsNone(log.timestamp)

    def test_save(self):
        log = RequestTokenLog(
            token=self.token,
            user=self.user
        ).save()
        self.assertIsNotNone(log.timestamp)
