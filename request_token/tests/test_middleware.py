# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponseNotAllowed, HttpResponseForbidden
from django.test import TestCase, RequestFactory

from jwt import exceptions

from ..compat import mock
from ..middleware import RequestTokenMiddleware
from ..models import RequestToken
from ..settings import JWT_QUERYSTRING_ARG


class MockSession(object):

    """Fake Session model used to support `session_key` property."""

    @property
    def session_key(self):
        return "foobar"


class MiddlewareTests(TestCase):

    """RequestTokenMiddleware tests."""

    def setUp(self):
        self.user = get_user_model().objects.create_user('zoidberg')
        self.factory = RequestFactory()
        self.middleware = RequestTokenMiddleware()
        self.token = RequestToken.objects.create_token(scope="foo")

    def get_request(self):
        request = self.factory.get('/?%s=%s' % (JWT_QUERYSTRING_ARG, self.token.jwt()))
        request.user = self.user
        request.session = MockSession()
        # request.token = self.token
        return request

    def test_process_request_assertions(self):
        request = self.factory.get('/')
        middleware = self.middleware

        process_request = middleware.process_request
        self.assertRaises(AssertionError, process_request, request)

        request.user = AnonymousUser()
        self.assertRaises(AssertionError, process_request, request)
        request.session = MockSession()

        self.assertIsNone(process_request(request))
        self.assertFalse(hasattr(request, 'token'))

    def test_process_request_without_token(self):
        request = self.factory.post('/')
        process_request = self.middleware.process_request
        request = self.factory.get('/')
        request.user = AnonymousUser()
        request.session = MockSession()
        self.assertIsNone(process_request(request))
        self.assertFalse(hasattr(request, 'token'))

    def test_process_request_with_valid_token(self):
        request = self.get_request()
        response = self.middleware.process_request(request)
        self.assertIsNone(response)
        self.assertEqual(request.token, self.token)

    def test_process_request_not_allowed(self):
        # POST requests not allowed
        request = self.factory.post('/?rt=foo')
        request.user = self.user
        request.session = MockSession()
        response = self.middleware.process_request(request)
        self.assertIsInstance(response, HttpResponseNotAllowed)
        self.assertEqual(response.status_code, 405)

    @mock.patch('request_token.middleware.logger')
    def test_process_request_token_error(self, mock_logger):
        # token decode error - request passes through _without_ a token
        request = self.factory.get('/?rt=foo')
        request.user = self.user
        request.session = MockSession()
        response = self.middleware.process_request(request)
        self.assertIsNone(response)
        self.assertFalse(hasattr(request, 'token'))
        self.assertEqual(mock_logger.exception.call_count, 1)

    @mock.patch('request_token.middleware.logger')
    def test_process_request_token_does_not_exist(self, mock_logger):
        request = self.get_request()
        self.token.delete()
        response = self.middleware.process_request(request)
        self.assertIsNone(response)
        self.assertFalse(hasattr(request, 'token'))
        self.assertEqual(mock_logger.exception.call_count, 1)

    @mock.patch.object(RequestToken, 'log')
    def test_process_exception(self, mock_log):
        request = self.get_request()
        request.token = self.token
        exception = exceptions.InvalidTokenError("bar")
        response = self.middleware.process_exception(request, exception)
        mock_log.assert_called_once_with(request, response, error=exception)

        # round it out with a non-token error
        response = self.middleware.process_exception(request, Exception("foo"))
        self.assertIsNone(response)
