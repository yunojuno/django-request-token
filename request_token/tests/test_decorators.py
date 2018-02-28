from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse, HttpRequest
from django.test import TestCase, RequestFactory

from ..decorators import use_request_token, _get_request_arg
from ..exceptions import ScopeError, TokenNotFoundError
from ..middleware import RequestTokenMiddleware
from ..models import RequestToken, RequestTokenLog
from ..settings import JWT_QUERYSTRING_ARG


@use_request_token(scope="foo")
def test_view_func(request):
    """Return decorated request / response objects."""
    response = HttpResponse("Hello, world!", status=200)
    return response


class TestClassBasedView(object):

    @use_request_token(scope="foobar")
    def test_response(self, request):
        """Return decorated request / response objects."""
        response = HttpResponse(str(request.token.id), status=200)
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
        self.middleware = RequestTokenMiddleware(get_response=lambda r: r)

    def _request(self, path, token, user):
        path = path + "?%s=%s" % (JWT_QUERYSTRING_ARG, token) if token else path
        request = self.factory.get(path)
        request.session = MockSession()
        request.user = user
        self.middleware(request)
        return request

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

        self.assertRaises(TokenNotFoundError, test_view_func2, request)

    def test_scope(self):
        token = RequestToken.objects.create_token(scope="foobar")
        request = self._request('/', token.jwt(), AnonymousUser())
        self.assertRaises(ScopeError, test_view_func, request)
        self.assertFalse(RequestTokenLog.objects.exists())

        RequestToken.objects.all().update(scope="foo")
        request = self._request('/', token.jwt(), AnonymousUser())
        response = test_view_func(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(RequestTokenLog.objects.exists())

    def test_class_based_view(self):
        """Test that CBV methods extract the request correctly."""
        cbv = TestClassBasedView()
        token = RequestToken.objects.create_token(scope="foobar")
        request = self._request('/', token.jwt(), AnonymousUser())
        response = cbv.test_response(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(int(response.content), token.id)
        self.assertTrue(RequestTokenLog.objects.exists())

    def test__get_request_arg(self):
        request = HttpRequest()
        cbv = TestClassBasedView()
        self.assertEqual(_get_request_arg(request), request)
        self.assertEqual(_get_request_arg(request, cbv), request)
        self.assertEqual(_get_request_arg(cbv, request), request)
