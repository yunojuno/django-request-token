from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory, TestCase

from request_token.decorators import _get_request_arg, use_request_token
from request_token.exceptions import ScopeError, TokenNotFoundError
from request_token.middleware import RequestTokenMiddleware
from request_token.models import RequestToken, RequestTokenLog
from request_token.settings import JWT_QUERYSTRING_ARG


@use_request_token(scope="foo")
def test_view_func(request):
    """Return decorated request / response objects."""
    response = HttpResponse("Hello, world!", status=200)
    return response


class TestClassBasedView:
    @use_request_token(scope="foobar")
    def get(self, request):
        """Return decorated request / response objects."""
        response = HttpResponse(str(request.token.id), status=200)
        return response


class MockSession:
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
        path = path + "?{}={}".format(JWT_QUERYSTRING_ARG, token) if token else path
        request = self.factory.get(path)
        request.session = MockSession()
        request.user = user
        self.middleware(request)
        return request

    def test_no_token(self):
        request = self._request("/", None, AnonymousUser())
        response = test_view_func(request)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(hasattr(request, "token"))
        self.assertFalse(RequestTokenLog.objects.exists())

        # now force a TokenNotFoundError, by requiring it in the decorator
        @use_request_token(scope="foo", required=True)
        def test_view_func2(request):
            pass

        self.assertRaises(TokenNotFoundError, test_view_func2, request)

    def test_scope(self):
        token = RequestToken.objects.create_token(scope="foobar")
        request = self._request("/", token.token, AnonymousUser())
        self.assertRaises(ScopeError, test_view_func, request)
        self.assertFalse(RequestTokenLog.objects.exists())

        RequestToken.objects.all().update(scope="foo")
        request = self._request("/", token.token, AnonymousUser())
        response = test_view_func(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(RequestTokenLog.objects.exists())

    def test_class_based_view(self):
        """Test that CBV methods extract the request correctly."""
        cbv = TestClassBasedView()
        token = RequestToken.objects.create_token(scope="foobar")
        request = self._request("/", token.token, AnonymousUser())
        response = cbv.get(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(int(response.content), token.id)
        self.assertTrue(RequestTokenLog.objects.exists())

    def test__get_request_arg(self):
        request = HttpRequest()
        cbv = TestClassBasedView()
        self.assertEqual(_get_request_arg(request), request)
        self.assertEqual(_get_request_arg(request, cbv), request)
        self.assertEqual(_get_request_arg(cbv, request), request)

    def test_delete_user__pass(self):
        user = User.objects.create_user("test_user")
        token = RequestToken.objects.create_token(user=user, scope="foo")
        request = self._request("/", token.token, user)
        assert User.objects.count() == 1

        @use_request_token(scope="foo", log=False)
        def delete_token_user_pass(request):
            request.user.delete()
            return HttpResponse("Hello, world!", status=204)

        response = delete_token_user_pass(request)
        assert response.status_code == 204
        assert User.objects.count() == 0

    def test_delete_user__fail(self):
        user = User.objects.create_user("test_user")
        token = RequestToken.objects.create_token(user=user, scope="foo")
        request = self._request("/", token.token, user)

        @use_request_token(scope="foo", log=True)
        def delete_token_user(request):
            request.user.delete()
            return HttpResponse("Hello, world!", status=204)

        self.assertRaises(ValueError, delete_token_user, request)
