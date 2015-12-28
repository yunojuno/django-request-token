# -*- coding: utf-8 -*-
"""django_jwt decorator tests."""
from jwt import exceptions

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import TransactionTestCase, RequestFactory

from django_jwt.decorators import use_jwt
from django_jwt.exceptions import MaxUseError, TargetUrlError
from django_jwt.models import RequestToken, RequestTokenLog


@use_jwt
def test_view_func(request):
    """Return HttpResponse object - request should be decorated with appropriate values."""
    return HttpResponse("Hello, world!")


class DecoratorTests(TransactionTestCase):

    """use_jwt decorator tests."""

    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, path, user):
        request = self.factory.get(path)
        request.user = user
        return request

    def _assertResponse(self, request, request_token, request_token_error, token_used):
        test_view_func(request)
        self.assertEqual(request.token, request_token)
        if request_token_error is not None:
            self.assertIsInstance(request.token_error, request_token_error)
        else:
            self.assertIsNone(request.token_error)
        self.assertEqual(request.token_used, token_used)

    def test_no_token(self):
        request = self._request('/', AnonymousUser())
        response = test_view_func(request)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(hasattr(request, 'token'))
        self.assertFalse(hasattr(request, 'jwt_error'))
        self.assertFalse(RequestTokenLog.objects.exists())

    def test_decode_error(self):
        request = self._request('/?jwt=foo', AnonymousUser())
        self._assertResponse(
            request,
            request_token=None,
            request_token_error=exceptions.DecodeError,
            token_used=False,
        )
        self.assertFalse(RequestTokenLog.objects.exists())

    def test_missing_token(self):
        token = RequestToken().save()
        RequestToken.objects.all().delete()
        request = self._request('/?jwt=' + token.encode(), AnonymousUser())
        self._assertResponse(
            request,
            request_token=None,
            request_token_error=RequestToken.DoesNotExist,
            token_used=False,
        )
        self.assertFalse(RequestTokenLog.objects.exists())

    def test_invalid_token(self):
        token = RequestToken(used_to_date=1, max_uses=1).save()
        request = self._request('/?jwt=' + token.encode(), AnonymousUser())
        self._assertResponse(
            request,
            request_token=token,
            request_token_error=MaxUseError,
            token_used=False,
        )
        self.assertFalse(RequestTokenLog.objects.exists())

    def test_valid_token_with_user(self):
        user = get_user_model().objects.create_user('zoidberg')
        token = RequestToken(user=user).save()
        # we're sending the request anonymously, but we have a valid
        # token, so we _should_ get the function run as the user.
        request = self._request('/?jwt=' + token.encode(), AnonymousUser())
        self._assertResponse(
            request,
            request_token=token,
            request_token_error=None,
            token_used=True,
        )
        self.assertTrue(RequestTokenLog.objects.exists())

    def test_valid_token_with_wrong_user(self):
        user1 = get_user_model().objects.create_user('zoidberg')
        user2 = get_user_model().objects.create_user('fry')
        token = RequestToken(user=user1).save()
        request = self._request('/?jwt=' + token.encode(), user2)
        self._assertResponse(
            request,
            request_token=token,
            request_token_error=exceptions.InvalidAudienceError,
            token_used=False,
        )
        self.assertFalse(RequestTokenLog.objects.exists())

    def test_valid_token_with_wrong_url(self):
        user = get_user_model().objects.create_user('zoidberg')
        token = RequestToken(user=user, target_url="/bar").save()
        request = self._request('/?jwt=' + token.encode(), user)
        self._assertResponse(
            request,
            request_token=token,
            request_token_error=TargetUrlError,
            token_used=False,
        )
        self.assertFalse(RequestTokenLog.objects.exists())
