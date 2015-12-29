# -*- coding: utf-8 -*-
"""django_jwt decorator tests."""
import datetime
from jwt import exceptions

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import TransactionTestCase, RequestFactory

from django_jwt.decorators import expiring_link
from django_jwt.exceptions import MaxUseError, TargetUrlError
from django_jwt.models import RequestToken, RequestTokenLog
from django_jwt.settings import JWT_QUERYSTRING_ARG


@expiring_link
def test_view_func(request):
    """Return HttpResponse object - request should be decorated with appropriate values."""
    return HttpResponse("Hello, world!")


class DecoratorTests(TransactionTestCase):

    """use_jwt decorator tests."""

    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, path, token, user):
        path = path + "?%s=%s" % (JWT_QUERYSTRING_ARG, token) if token else path
        request = self.factory.get(path)
        request.user = user
        return request

    def _assertResponse(self, request, token, token_error):
        response = test_view_func(request)
        self.assertEqual(request.token, token)
        if token_error is not None:
            self.assertIsInstance(response.token_error, token_error)
        else:
            self.assertIsNone(response.token_error)

    def test_no_token(self):
        request = self._request('/', None, AnonymousUser())
        response = test_view_func(request)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(hasattr(request, 'token'))
        self.assertFalse(hasattr(request, 'jwt_error'))
        self.assertFalse(RequestTokenLog.objects.exists())

    def test_decode_error(self):
        request = self._request('/', 'foo', AnonymousUser())
        self._assertResponse(
            request,
            token=None,
            token_error=exceptions.DecodeError,
        )
        self.assertFalse(RequestTokenLog.objects.exists())

    def test_missing_token(self):
        token = RequestToken().save()
        RequestToken.objects.all().delete()
        request = self._request('/', token.jwt(), AnonymousUser())
        self._assertResponse(
            request,
            token=None,
            token_error=RequestToken.DoesNotExist,
        )
        self.assertFalse(RequestTokenLog.objects.exists())

    def test_invalid_token_decode(self):
        token = RequestToken(expiration_time=datetime.datetime(1970, 1, 1)).save()
        request = self._request('/', token.jwt(), AnonymousUser())
        token.max_uses = 100
        token.expiration_time = datetime.datetime(1970, 1, 1)
        token.save()
        self._assertResponse(
            request,
            token=None,  # token cannot be decoded, so won't be loaded from DB
            token_error=exceptions.InvalidTokenError,
        )

        self.assertFalse(RequestTokenLog.objects.exists())

    def test_invalid_token(self):
        token = RequestToken(used_to_date=1, max_uses=1).save()
        request = self._request('/', token.jwt(), AnonymousUser())
        self._assertResponse(
            request,
            token=token,
            token_error=MaxUseError,
        )

        token.max_uses = 100
        token.target_url = '/foo'
        token.save()
        request = self._request('/', token.jwt(), AnonymousUser())
        self._assertResponse(
            request,
            token=token,
            token_error=TargetUrlError,
        )

    def test_valid_token_with_user(self):
        user = get_user_model().objects.create_user('zoidberg')
        token = RequestToken(user=user).save()
        # we're sending the request anonymously, but we have a valid
        # token, so we _should_ get the function run as the user.
        request = self._request('/', token.jwt(), AnonymousUser())
        self._assertResponse(
            request,
            token=token,
            token_error=None,
        )
        self.assertTrue(RequestTokenLog.objects.exists())

    def test_valid_token_with_wrong_user(self):
        user1 = get_user_model().objects.create_user('zoidberg')
        user2 = get_user_model().objects.create_user('fry')
        token = RequestToken(user=user1).save()
        request = self._request('/', token.jwt(), user2)
        self._assertResponse(
            request,
            token=token,
            token_error=exceptions.InvalidAudienceError,
        )
        self.assertFalse(RequestTokenLog.objects.exists())

    def test_valid_token_with_wrong_url(self):
        user = get_user_model().objects.create_user('zoidberg')
        token = RequestToken(user=user, target_url="/bar").save()
        request = self._request('/', token.jwt(), user)
        self._assertResponse(
            request,
            token=token,
            token_error=TargetUrlError,
        )
        self.assertFalse(RequestTokenLog.objects.exists())
