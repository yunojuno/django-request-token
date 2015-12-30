# -*- coding: utf-8 -*-
"""django_jwt decorator tests."""
import datetime
from jwt import exceptions

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse, HttpResponseForbidden
from django.test import TransactionTestCase, RequestFactory

from django_jwt.decorators import expiring_link, respond_to_error
from django_jwt.exceptions import MaxUseError, ScopeError
from django_jwt.models import RequestToken, RequestTokenLog
from django_jwt.settings import JWT_QUERYSTRING_ARG
from django_jwt.middleware import RequestTokenMiddleware


@expiring_link(scope="foo")
def test_view_func(request):
    """Return decorated request / response objects."""
    return HttpResponse("Hello, world!", status=200)


class MockSession(object):

    """Fake Session model used to support `session_key` property."""

    @property
    def session_key(self):
        return "foobar"


class DecoratorTests(TransactionTestCase):

    """use_jwt decorator tests."""

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = RequestTokenMiddleware()

    def _request(self, path, token, user):
        path = path + "?%s=%s" % (JWT_QUERYSTRING_ARG, token) if token else path
        request = self.factory.get(path)
        request.session = MockSession()
        request.user = user
        self.middleware.process_request(request)
        return request

    def _assertResponse(self, request, response_type, token=None, response_err=None):
        response = test_view_func(request)
        self.assertIsInstance(response, response_type)
        if response_err:
            self.assertIsInstance(response.error, response_err)
        if token is None:
            self.assertFalse(hasattr(request, 'token'))
            self.assertFalse(RequestTokenLog.objects.exists())
        else:
            self.assertEqual(request.token, token)
            self.assertTrue(RequestTokenLog.objects.exists())

    def test_respond_to_error(self):
        ex = Exception("foo")
        response = respond_to_error("bar", ex)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.error, ex)

    def test_no_token(self):
        request = self._request('/', None, AnonymousUser())
        response = test_view_func(request)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(hasattr(request, 'token'))
        self.assertFalse(RequestTokenLog.objects.exists())

    def test_missing_token(self):
        token = RequestToken.objects.create_token(scope="foo")
        RequestToken.objects.all().delete()
        request = self._request('/', token.jwt(), AnonymousUser())
        self._assertResponse(request, HttpResponseForbidden, response_err=RequestToken.DoesNotExist)

    def test_max_token_use(self):
        token = RequestToken.objects.create_token(scope="foo", used_to_date=1)
        request = self._request('/', token.jwt(), AnonymousUser())
        self._assertResponse(request, HttpResponseForbidden, response_err=MaxUseError)

    def test_scope(self):
        token = RequestToken.objects.create_token(scope="foobar")
        request = self._request('/', token.jwt(), AnonymousUser())
        self._assertResponse(request, HttpResponseForbidden, response_err=ScopeError)

    def test_valid_token_with_user(self):
        user = get_user_model().objects.create_user('zoidberg')
        token = RequestToken.objects.create_token(scope="foo", user=user)
        # we're sending the request anonymously, but we have a valid
        # token, so we _should_ get the function run as the user.
        request = self._request('/', token.jwt(), AnonymousUser())
        self._assertResponse(
            request,
            response_type=HttpResponse,
            token=token
        )
        self.assertTrue(RequestTokenLog.objects.exists())

    def test_valid_token_with_wrong_user(self):
        user1 = get_user_model().objects.create_user('zoidberg', password='secret')
        user2 = get_user_model().objects.create_user('fry', password='secret')
        token = RequestToken.objects.create_token(scope="foo", user=user1)
        request = self._request('/', token.jwt(), user2)
        self._assertResponse(
            request,
            response_type=HttpResponseForbidden,
            response_err=exceptions.InvalidAudienceError,
        )
