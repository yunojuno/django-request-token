# -*- coding: utf-8 -*-
"""request_token decorator tests."""
import mock

from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse, HttpResponseForbidden
from django.test import TestCase, RequestFactory

from ..decorators import use_request_token, respond_to_error
from ..exceptions import ScopeError, TokenNotFoundError
from ..models import RequestToken, RequestTokenLog
from ..settings import JWT_QUERYSTRING_ARG
from ..middleware import RequestTokenMiddleware


@use_request_token(scope="foo")
def test_view_func(request):
    """Return decorated request / response objects."""
    response = HttpResponse("Hello, world!", status=200)
    return response


class MockSession(object):

    """Fake Session model used to support `session_key` property."""

    @property
    def session_key(self):
        return "foobar"


class DecoratorTests(TestCase):

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

    def test_respond_to_error(self):
        ex = Exception("foo")
        response = respond_to_error("bar", ex)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.error, ex)

        from request_token import decorators
        with mock.patch.multiple(
            decorators,
            loader=mock.Mock(),
            FOUR03_TEMPLATE='foo.html'
        ):
            response = respond_to_error("bar", ex)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.error, ex)
            decorators.loader.render_to_string.assert_called_once_with(
                'foo.html',
                context={'token_error': 'Invalid URL token: bar'}
            )

    def test_no_token(self):
        request = self._request('/', None, AnonymousUser())
        response = test_view_func(request)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(hasattr(request, 'token'))
        self.assertFalse(RequestTokenLog.objects.exists())

        # now force a TokenNotFoundError, by requiring it in the decorator
        @use_request_token(scope="foo", required=True)
        def test_view_func2(request):
            pass

        response = test_view_func2(request)
        self.assertIsInstance(response, HttpResponseForbidden)
        self.assertIsInstance(response.error, TokenNotFoundError)

    def test_scope(self):
        token = RequestToken.objects.create_token(scope="foobar")
        request = self._request('/', token.jwt(), AnonymousUser())
        response = test_view_func(request)
        self.assertIsInstance(response, HttpResponseForbidden)
        self.assertIsInstance(response.error, ScopeError)
        self.assertFalse(RequestTokenLog.objects.exists())

        RequestToken.objects.all().update(scope="foo")
        request = self._request('/', token.jwt(), AnonymousUser())
        response = test_view_func(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(RequestTokenLog.objects.exists())
