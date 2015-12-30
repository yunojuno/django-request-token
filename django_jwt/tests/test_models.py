# -*- coding: utf-8 -*-
"""django_jwt model tests."""
import json
import mock

from jwt.exceptions import InvalidAudienceError

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError
from django.http import HttpResponse
from django.test import TransactionTestCase, RequestFactory
from django.utils.timezone import now as tz_now

from django_jwt.models import RequestToken, RequestTokenLog
from django_jwt.exceptions import MaxUseError
from django_jwt.utils import to_seconds


class RequestTokenTests(TransactionTestCase):

    """RequestToken model property and method tests."""

    def setUp(self):
        self.user = get_user_model().objects.create_user('zoidberg')

    def test_defaults(self):
        token = RequestToken()
        self.assertIsNone(token.user)
        self.assertEqual(token.scope, '')
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
        self.assertEqual(token.scope, '')
        self.assertIsNone(token.expiration_time)
        self.assertIsNone(token.not_before_time)
        self.assertEqual(token.data, "{}")
        self.assertIsNotNone(token.issued_at)
        self.assertEqual(token.max_uses, 1)
        self.assertEqual(token.used_to_date, 0)

        token.issued_at = None
        token = token.save(update_fields=['issued_at'])
        self.assertIsNone(token.issued_at)

    def test_default_claims(self):
        token = RequestToken()
        # raises error with no id set - put into context manager as it's
        # an attr, not a callable
        self.assertTrue(len(token.default_claims), 2)
        self.assertEqual(token.max, 1)
        self.assertEqual(token.sub, '')
        self.assertIsNone(token.jti)
        self.assertIsNone(token.aud)
        self.assertIsNone(token.exp)
        self.assertIsNone(token.nbf)
        self.assertIsNone(token.iat)

        # now let's set some properties
        token.user = self.user
        self.assertEqual(token.aud, self.user.id)
        self.assertTrue(len(token.default_claims), 3)

        now = tz_now()
        now_sec = to_seconds(now)

        token.expiration_time = now
        self.assertEqual(token.exp, now_sec)
        self.assertTrue(len(token.default_claims), 4)

        token.not_before_time = now
        self.assertEqual(token.nbf, now_sec)
        self.assertEqual(len(token.default_claims), 5)

        # saving updates the id and issued_at timestamp
        with mock.patch('django_jwt.models.tz_now', lambda: now):
            token.save()
            self.assertEqual(token.iat, now_sec)
            self.assertEqual(token.jti, token.id)
            self.assertEqual(len(token.default_claims), 7)

    def test_payload(self):
        token = RequestToken()
        claims = token.default_claims
        self.assertEqual(token.payload, claims)
        token.data = json.dumps({'foo': 123})
        claims.update({'foo': 123})
        self.assertEqual(token.payload, claims)

    def test__validate_max_uses(self):
        token = RequestToken()
        token._validate_max_uses()
        token.used_to_date = token.max_uses
        self.assertRaises(MaxUseError, token._validate_max_uses)
        token.used_to_date = token.max_uses + 1
        self.assertRaises(MaxUseError, token._validate_max_uses)

    # def test__validate_request_path(self):
    #     # target_url is None
    #     token = RequestToken()
    #     factory = RequestFactory()
    #     request = factory.get('/foo')
    #     # no target_path will get through ok
    #     token._validate_request_path(request.path)
    #     # target_path and request.path mismatch
    #     token.target_url = '/bar'
    #     self.assertRaises(TargetUrlError, token._validate_request_path, request.path)

    def test__validate_request_user(self):

        # token user is None
        token = RequestToken()
        factory = RequestFactory()
        request = factory.get('/foo')

        # user is unchanged as we don't specify a token.user
        anon = AnonymousUser()
        request.user = anon
        token._validate_request_user(request.user)

        # authenticated user, but no token user, so should pass through
        token.user = self.user
        token._validate_request_user(request.user)

        # authenticated user that matches the token - OK
        request.user = self.user
        token._validate_request_user(request.user)

        # authenticated user that does not match the token - FAIL
        wrong_user = get_user_model().objects.create_user(username="Finbar")
        request.user = wrong_user
        self.assertRaises(InvalidAudienceError, token._validate_request_user, request.user)

    def test_validate_request(self):
        token = RequestToken(user=self.user)
        factory = RequestFactory()
        request = factory.get('/foo')
        request.user = self.user
        token.validate_request(request)
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

    def test_create_token(self):
        self.assertRaises(TypeError, RequestToken.objects.create_token)
        RequestToken.objects.create_token(scope="foo")
        self.assertEqual(RequestToken.objects.get().scope, 'foo')


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

        log.timestamp = None
        self.assertRaises(IntegrityError, log.save, update_fields=['timestamp'])
