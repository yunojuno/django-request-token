# -*- coding: utf-8 -*-
"""request_token middleware tests."""
import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponseForbidden, HttpResponseNotAllowed
from django.test import TestCase, RequestFactory

from jwt import exceptions

from ..models import RequestToken
from ..settings import JWT_QUERYSTRING_ARG
from ..middleware import RequestTokenMiddleware


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

    def test_process_request_with_token(self):

        def new_request(jwt, user=self.user, session=MockSession()):
            request = self.factory.get('/?%s=%s' % (JWT_QUERYSTRING_ARG, jwt))
            request.user = user
            request.session = session
            return request

        # has a valid token
        token = RequestToken.objects.create_token(scope="foo")
        request = new_request(token.jwt())
        self.assertIsNone(self.middleware.process_request(request))
        self.assertEqual(request.token, token)

    def test_process_request_not_allowed(self):

        def new_request(jwt, user=self.user, session=MockSession()):
            request = self.factory.post('/?%s=%s' % (JWT_QUERYSTRING_ARG, jwt))
            request.user = user
            request.session = session
            return request

        # has a valid token
        token = RequestToken(id=1, scope="foo")
        request = new_request(token.jwt())
        response = self.middleware.process_request(request)
        self.assertIsInstance(response, HttpResponseNotAllowed)
        self.assertFalse(hasattr(response, 'error'))
        self.assertFalse(hasattr(request, 'token'))
        self.assertEqual(response.status_code, 405)

    def test_process_request_forbidden(self):

        def new_request(jwt, user=self.user, session=MockSession()):
            request = self.factory.get('/?%s=%s' % (JWT_QUERYSTRING_ARG, jwt))
            request.user = user
            request.session = session
            return request

        # has an invalid token
        request = new_request("foo")  # this won't decode
        response = self.middleware.process_request(request)
        self.assertIsInstance(response, HttpResponseForbidden)
        self.assertIsInstance(response.error, exceptions.DecodeError)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(hasattr(request, 'token'))

        # test with a FOUR03_TEMPLATE setting
        from request_token import middleware
        with mock.patch.multiple(middleware, FOUR03_TEMPLATE='foo.html', loader=mock.Mock()):
            response = self.middleware.process_request(request)
            self.assertIsInstance(response, HttpResponseForbidden)
            self.assertIsInstance(response.error, exceptions.DecodeError)
            self.assertEqual(response.status_code, 403)
            self.assertFalse(hasattr(request, 'token'))
            # this has been mocked out
            middleware.loader.render_to_string.assert_called_once_with(
                'foo.html',
                context={'token_error': 'Temporary link token error: foobar'}
            )
